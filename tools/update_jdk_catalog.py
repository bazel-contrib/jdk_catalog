#!/usr/bin/env python3
"""Update the non-LTS JDK pin catalog (jdk/repositories.bzl) from vendor APIs.

Fetches the latest GA build of the configured JDK major version from Azul
(Zulu Community) for the mainstream platforms and from Adoptium (Temurin)
for the architectures Azul does not publish, then regenerates the
_JDK<N>_CONFIGS pin list in place.

  tools/update_jdk_catalog.py              # regenerate if a newer build exists
  tools/update_jdk_catalog.py --dry-run    # report only; exit 1 if outdated
  tools/update_jdk_catalog.py --java-version 27

Network access goes through curl so the script does not depend on a Python
TLS trust store. sha256 values come from the vendors' own metadata, so no
archives are downloaded.
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

AZUL = "https://api.azul.com/metadata/v1/zulu/packages/"
ADOPTIUM = "https://api.adoptium.net/v3/assets/latest/{v}/hotspot"

# name-suffix, os constraint, cpu constraint, azul os, azul arch, archive, patch
AZUL_PLATFORMS = [
    ("linux", "linux", "x86_64", "linux", "x64", "tar.gz", None),
    ("linux_aarch64", "linux", "aarch64", "linux", "aarch64", "tar.gz", None),
    ("macos", "macos", "x86_64", "macos", "x64", "tar.gz", "ln -s Contents/Home/* ."),
    ("macos_aarch64", "macos", "aarch64", "macos", "aarch64", "tar.gz",
     "ln -s Contents/Home/* ."),
    ("win", "windows", "x86_64", "windows", "x64", "zip", None),
]

# name-suffix, cpu constraint, adoptium arch
TEMURIN_PLATFORMS = [
    ("linux_ppc64le", "ppc64le", "ppc64le"),
    ("linux_riscv64", "riscv64", "riscv64"),
    ("linux_s390x", "s390x", "s390x"),
]


def curl_json(url):
    out = subprocess.run(["curl", "-sSL", url], capture_output=True, text=True,
                         check=True).stdout
    return json.loads(out)


def azul_build(java_version, azul_os, arch, archive_type):
    """The latest GA, plain Community (no CRaC/FX/musl) Azul build."""
    query = (f"{AZUL}?java_version={java_version}&os={azul_os}&arch={arch}"
             f"&archive_type={archive_type}&java_package_type=jdk"
             "&javafx_bundled=false&crac_supported=false&release_status=ga"
             "&availability_types=CA&latest=true&page_size=25")
    plain = [p for p in curl_json(query)
             if "-ca-jdk" in p["name"] and "musl" not in p["name"]
             and "crac" not in p["name"] and "-fx-" not in p["name"]]
    if not plain:
        raise SystemExit(f"No plain Azul CA build for os={azul_os} arch={arch}")
    pick = plain[0]
    name = pick["name"]
    strip_prefix = name[:-7] if name.endswith(".tar.gz") else name[:-4]
    sha256 = curl_json(f"{AZUL}{pick['package_uuid']}")["sha256_hash"]
    return pick["download_url"], strip_prefix, sha256


def temurin_build(java_version, arch):
    query = (f"{ADOPTIUM.format(v=java_version)}?architecture={arch}&os=linux"
             "&image_type=jdk&vendor=eclipse")
    assets = curl_json(query)
    if not assets:
        raise SystemExit(f"No Temurin JDK {java_version} build for arch={arch}")
    pkg = assets[0]["binary"]["package"]
    # Match the repository's literal '+' URL style, not the %2B form.
    return pkg["link"].replace("%2B", "+"), assets[0]["release_name"], pkg["checksum"]


def fetch_configs(java_version):
    configs = []
    for suffix, os_c, cpu_c, azul_os, arch, archive, patch in AZUL_PLATFORMS:
        url, strip_prefix, sha256 = azul_build(java_version, azul_os, arch, archive)
        configs.append(dict(name=f"remotejdk{java_version}_{suffix}", os=os_c,
                            cpu=cpu_c, sha256=sha256, strip_prefix=strip_prefix,
                            url=url, patch=patch))
    for suffix, cpu_c, arch in TEMURIN_PLATFORMS:
        url, strip_prefix, sha256 = temurin_build(java_version, arch)
        configs.append(dict(name=f"remotejdk{java_version}_{suffix}", os="linux",
                            cpu=cpu_c, sha256=sha256, strip_prefix=strip_prefix,
                            url=url, patch=None))
    return configs


def render(configs, java_version):
    blocks = []
    for c in configs:
        lines = [
            "    struct(",
            f'        name = "{c["name"]}",',
            f'        target_compatible_with = ["@platforms//os:{c["os"]}", '
            f'"@platforms//cpu:{c["cpu"]}"],',
            f'        sha256 = "{c["sha256"]}",',
            f'        strip_prefix = "{c["strip_prefix"]}",',
            "        urls = [",
            f'            "{c["url"]}",',
            "        ],",
            f'        version = "{java_version}",',
        ]
        if c["patch"]:
            lines.append(f'        patch_cmds = ["{c["patch"]}"],')
        lines.append("    ),")
        blocks.append("\n".join(lines))
    return "\n".join(blocks)


def current_shas(body, java_version):
    """Map remotejdk<N>_* name -> sha256 from the existing list body."""
    out = {}
    for m in re.finditer(
            r'name = "(remotejdk%s_[^"]+)".*?sha256 = "([0-9a-f]+)"' % java_version,
            body, re.DOTALL):
        out[m.group(1)] = m.group(2)
    return out


def version_of(configs):
    for c in configs:
        m = re.search(r"jdk[-]?(\d+(?:\.\d+)+)", c["strip_prefix"])
        if m:
            return m.group(1)
    return "?"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--java-version", default="27")
    ap.add_argument("--dry-run", action="store_true",
                    help="report only; exit 1 if an update is available")
    args = ap.parse_args()
    jv = args.java_version

    repo_file = Path(__file__).resolve().parents[1] / "jdk" / "repositories.bzl"
    text = repo_file.read_text()
    block = re.search(r"(_JDK%s_CONFIGS = \[\n)(.*?)(\n\]\n)" % jv, text, re.DOTALL)
    if not block:
        raise SystemExit(f"_JDK{jv}_CONFIGS list not found in {repo_file}")

    configs = fetch_configs(jv)
    latest = {c["name"]: c["sha256"] for c in configs}
    current = current_shas(block.group(2), jv)
    up_to_date = latest == current

    if up_to_date:
        print(f"JDK {jv} catalog is up to date ({version_of(configs)}).")
        return 0

    print(f"JDK {jv} update available -> {version_of(configs)}")
    for name, sha in latest.items():
        if current.get(name) != sha:
            print(f"  {name}: {current.get(name, '(new)')[:12]} -> {sha[:12]}")

    if args.dry_run:
        print("Run without --dry-run to regenerate jdk/repositories.bzl.")
        return 1

    new_text = text[:block.start(2)] + render(configs, jv) + text[block.end(2):]
    repo_file.write_text(new_text)
    buildifier = shutil.which("buildifier")
    if buildifier:
        subprocess.run([buildifier, str(repo_file)], check=True)
    print(f"Regenerated {repo_file.relative_to(repo_file.parents[1])}. "
          "Review, stage and push.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
