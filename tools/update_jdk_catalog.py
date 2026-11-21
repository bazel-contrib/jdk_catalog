#!/usr/bin/env python3
"""Refresh JDK catalogs and their generator inputs from vendor metadata.

Fetches GA builds from Azul (Zulu Community), Adoptium (Temurin), Microsoft,
and BellSoft Liberica for the existing platforms. Updates pin lists and LTS generator
release strings together. Temurin LTS releases must cover every configured
architecture; non-LTS releases may differ by architecture.

  tools/update_jdk_catalog.py --all        # refresh LTS and non-LTS catalogs
  tools/update_jdk_catalog.py --all --dry-run
  tools/update_jdk_catalog.py              # refresh JDK 27 only (legacy default)
  tools/update_jdk_catalog.py --java-version 27
  tools/update_jdk_catalog.py --java-version 25 --verify-archive-roots

Network access goes through curl so the script does not depend on a Python
TLS trust store. Checksums come from published vendor metadata. Archive-root
checks read only archive headers, including the Microsoft build number that
is absent from its download filename. No full JDK archives are downloaded.
"""

import argparse
import ast
import io
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tarfile
import tempfile
import zlib
from pathlib import Path
from urllib.parse import quote, urlencode

AZUL = "https://api.azul.com/metadata/v1/zulu/packages/"
ADOPTIUM = "https://api.adoptium.net/v3/assets/latest/{v}/hotspot"
MICROSOFT_DOWNLOADS = "https://learn.microsoft.com/en-us/java/openjdk/download"

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


def curl_text(url):
    return subprocess.run(
        ["curl", "--fail", "--silent", "--show-error", "--location", "--retry", "2",
         "--max-time", "60", url], capture_output=True, text=True,
        check=True).stdout


def curl_json(url):
    return json.loads(curl_text(url))


def archive_root(url, archive_type):
    """Inspect an archive header without downloading the whole archive."""
    proc = subprocess.Popen(
        ["curl", "--fail", "--silent", "--show-error", "--location", "--retry", "2",
         "--max-time", "60", "--range", "0-262143", url],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        data = proc.stdout.read(262144)
    finally:
        proc.stdout.close()
        proc.stdout = None
        if proc.poll() is None:
            proc.terminate()
        _, error = proc.communicate()
    if not data:
        raise ValueError(f"Cannot read archive header: {url}: {error.decode().strip()}")
    if archive_type == "zip":
        if data[:4] != b"PK\x03\x04":
            raise ValueError(f"Not a ZIP archive: {url}")
        name_length = struct.unpack_from("<H", data, 26)[0]
        name = data[30:30 + name_length].decode()
    else:
        raw = zlib.decompressobj(16 + zlib.MAX_WBITS).decompress(data, 16 * 1024 * 1024)
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as archive:
            first = archive.next()
            if first is None:
                raise ValueError(f"Empty archive: {url}")
            name = first.name
    root = name.removeprefix("./").split("/")[0]
    if not root or root in (".", ".."):
        raise ValueError(f"Invalid archive root {root!r}: {url}")
    return root


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
        raise ValueError(f"No plain Azul CA build for os={azul_os} arch={arch}")
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
        raise ValueError(f"No Temurin JDK {java_version} build for arch={arch}")
    pkg = assets[0]["binary"]["package"]
    # Match the repository's literal '+' URL style, not the %2B form.
    return pkg["link"].replace("%2B", "+"), assets[0]["release_name"], pkg["checksum"]


def bellsoft_build(java_version):
    """The full Liberica JDK for Windows ARM64, matching Bazel's provider."""
    query = urlencode({
        "version-feature": java_version, "version-modifier": "latest",
        "os": "windows", "arch": "arm", "bitness": 64,
        "package-type": "zip", "bundle-type": "jdk",
    })
    builds = [b for b in curl_json("https://api.bell-sw.com/v1/liberica/releases?" + query)
              if b["GA"] and b["bundleType"] == "jdk" and b["featureVersion"] == int(java_version)]
    if len(builds) != 1:
        raise ValueError(f"Expected one Liberica JDK {java_version} Windows ARM64 build")
    build = builds[0]
    # BellSoft's discovery response exposes SHA-1; the published GitHub release
    # asset metadata supplies the SHA-256 required by remote_java_repository.
    release = curl_json("https://api.github.com/repos/bell-sw/Liberica/releases/tags/"
                        + quote(build["version"], safe=""))
    assets = [a for a in release["assets"] if a["name"] == build["filename"]]
    if len(assets) != 1 or not (assets[0].get("digest") or "").startswith("sha256:"):
        raise ValueError(f"Missing published SHA-256 for {build['filename']}")
    url = assets[0]["browser_download_url"]
    return url, archive_root(url, "zip"), assets[0]["digest"].removeprefix("sha256:")


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
    url, strip_prefix, sha256 = bellsoft_build(java_version)
    configs.append(dict(name=f"remotejdk{java_version}_win_arm64", os="windows",
                        cpu="arm64", sha256=sha256, strip_prefix=strip_prefix,
                        url=url, patch=None))
    return configs


def version_of(configs):
    for c in configs:
        m = re.search(r"jdk[-]?(\d+(?:\.\d+)+)", c["strip_prefix"])
        if m:
            return m.group(1)
    return "?"


def common_temurin_release(java_version, arches):
    """Choose the newest GA release containing all configured architectures."""
    for page in range(5):
        query = urlencode(dict(os="linux", image_type="jdk", vendor="eclipse",
                               page_size=10, page=page, sort_order="DESC"))
        releases = curl_json(
            f"https://api.adoptium.net/v3/assets/feature_releases/{java_version}/ga?{query}")
        for release in releases:
            binaries = {b["architecture"]: b for b in release["binaries"]}
            if set(arches) <= binaries.keys():
                return release["release_name"], binaries
        if len(releases) < 10:
            break
    raise ValueError(f"No common Temurin JDK {java_version} release for {arches}")


def assignment(source, name):
    """Read a literal assignment without executing Starlark as Python."""
    for node in ast.parse(source).body:
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name) and node.targets[0].id == name):
            return node.value
    raise ValueError(f"Missing {name}")


def replace_source_values(source, releases, overrides):
    """Update only release strings and the Microsoft archive-prefix override."""
    edits = []
    offsets = [0]
    for line in source.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))

    def replace(node, value):
        if ast.literal_eval(node) != value:
            edits.append((offsets[node.lineno - 1] + node.col_offset,
                          offsets[node.end_lineno - 1] + node.end_col_offset,
                          json.dumps(value)))

    def entries(node):
        return {ast.literal_eval(k): v for k, v in zip(node.keys, node.values)}

    for major, vendors in entries(assignment(source, "_RELEASE_CONFIGS")).items():
        for vendor, config in entries(vendors).items():
            if (major, vendor) in releases:
                replace(entries(config)["release"], releases[major, vendor])
    prefix_nodes = entries(assignment(source, "_STRIP_PREFIX_OVERRIDES"))
    for name, prefix in overrides.items():
        if name not in prefix_nodes:
            raise ValueError(f"Missing strip-prefix override for {name}")
        replace(prefix_nodes[name], prefix)
    for start, end, value in sorted(edits, reverse=True):
        source = source[:start] + value + source[end:]
    return source


def repo_name(major, os_name, cpu):
    prefix = "remote_jdk" if major == "8" else "remotejdk"
    platform = "win" if os_name == "windows" and major != "8" else os_name
    suffix = "" if cpu == "x86_64" else "_" + cpu
    return f"{prefix}{major}_{platform}{suffix}"


def fetch_lts(major, vendors):
    """Return pin updates and generator releases, keeping platform coverage fixed."""
    pins, releases, overrides = {}, {}, {}
    for vendor, config in vendors.items():
        platforms = [(os_name, cpu) for os_name, cpus in config["platforms"].items()
                     for cpu in cpus]
        if vendor == "adoptopenjdk":
            print(f"JDK {major}: retaining legacy AdoptOpenJDK {config['release']} "
                  "(no Temurin replacement for the configured s390x platform).")
            continue
        if vendor == "adoptium":
            if any(os_name != "linux" for os_name, _ in platforms):
                raise ValueError("Only Linux Temurin platforms are supported")
            release, binaries = common_temurin_release(major, [cpu for _, cpu in platforms])
            releases[major, vendor] = release.removeprefix("jdk-")
            for os_name, cpu in platforms:
                package = binaries[cpu]["package"]
                pins[repo_name(major, os_name, cpu)] = dict(
                    url=package["link"].replace("%2B", "+"),
                    strip_prefix=release, sha256=package["checksum"])
        elif vendor == "zulu":
            selected = set()
            for os_name, cpu in platforms:
                arch = {"x86_64": "x64", "arm64": "aarch64"}.get(cpu, cpu)
                ext = "zip" if os_name == "windows" else "tar.gz"
                url, prefix, sha = azul_build(major, os_name, arch, ext)
                platform = {"windows": "win", "macos": "macosx"}.get(os_name, os_name)
                suffix = f"-{platform}_{arch}"
                if not prefix.startswith("zulu") or not prefix.endswith(suffix):
                    raise ValueError(f"Unexpected Zulu archive layout: {prefix}")
                selected.add(prefix[4:-len(suffix)])
                pins[repo_name(major, os_name, cpu)] = dict(
                    url=url, strip_prefix=prefix, sha256=sha)
            if len(selected) != 1:
                raise ValueError(f"Zulu JDK {major} release differs across platforms: {selected}")
            releases[major, vendor] = selected.pop()
        elif vendor == "microsoft":
            if platforms != [("windows", "arm64")]:
                raise ValueError("Only Microsoft Windows ARM64 is supported")
            versions = set(re.findall(
                rf"microsoft-jdk-({major}(?:\.\d+)+)-windows-aarch64\.zip",
                curl_text(MICROSOFT_DOWNLOADS)))
            if not versions:
                raise ValueError(f"No Microsoft JDK {major} Windows ARM64 download found")
            release = max(versions, key=lambda v: tuple(map(int, v.split("."))))
            url = f"https://aka.ms/download-jdk/microsoft-jdk-{release}-windows-aarch64.zip"
            sha = curl_text(url + ".sha256sum.txt").split()[0]
            # The filename omits the build number used in the archive root.
            prefix = archive_root(url, "zip")
            if not prefix.startswith(f"jdk-{release}+"):
                raise ValueError(f"Unexpected Microsoft archive root: {prefix}")
            name = repo_name(major, "windows", "arm64")
            pins[name] = dict(url=url, strip_prefix=prefix, sha256=sha)
            releases[major, vendor] = release
            overrides[name] = prefix
        else:
            raise ValueError(f"Unsupported vendor {vendor}")
    return pins, releases, overrides


def replace_pins(source, symbol, updates, verify_roots=False):
    block = re.search(r"(" + symbol + r" = \[\n)(.*?)(\n\]\n)", source, re.DOTALL)
    if not block:
        raise ValueError(f"Missing {symbol} pin list")
    remaining = set(updates)

    def replace(match):
        body = match[0]
        name = re.search(r'name = "([^"]+)"', body)[1]
        if name not in updates:
            return body
        remaining.remove(name)
        pin = updates[name]
        if not re.fullmatch(r"[0-9a-f]{64}", pin["sha256"]):
            raise ValueError(f"Invalid vendor SHA-256 for {name}")
        if verify_roots:
            ext = "zip" if pin["url"].endswith(".zip") else "tar.gz"
            actual = archive_root(pin["url"], ext)
            if actual != pin["strip_prefix"]:
                raise ValueError(f"Archive root mismatch for {name}: {actual}")
        urls = [pin["url"]]
        # LTS entries retain the mirror policy used by repositories_util.bzl.
        if symbol == "REMOTE_JDK_CONFIGS_LIST":
            urls.append("https://mirror.bazel.build/" + pin["url"].removeprefix("https://"))
        body = re.sub(r'sha256 = "[^"]+"', 'sha256 = ' + json.dumps(pin["sha256"]), body)
        body = re.sub(r'strip_prefix = "[^"]+"',
                      'strip_prefix = ' + json.dumps(pin["strip_prefix"]), body)
        def replace_urls(match):
            if "\n" in match[0]:
                return ("urls = [\n"
                        + "".join("            " + json.dumps(url) + ",\n" for url in urls)
                        + "        ]")
            return "urls = " + json.dumps(urls)

        return re.sub(r"urls = \[.*?\]", replace_urls, body, flags=re.DOTALL)

    body = re.sub(r"    struct\(\n.*?\n    \),", replace, block[2], flags=re.DOTALL)
    if remaining:
        raise ValueError(f"Refusing to add unregistered JDK repositories: {sorted(remaining)}")
    return source[:block.start(2)] + body + source[block.end(2):]


def plan_updates(root, versions, verify_roots=False):
    source_file = root / "jdk/repositories_util.bzl"
    source = source_file.read_text()
    configs = ast.literal_eval(assignment(source, "_RELEASE_CONFIGS"))
    unknown = set(versions) - configs.keys() - {"27"}
    if unknown:
        raise ValueError(f"Unconfigured JDK major versions: {sorted(unknown)}")
    pins, releases, overrides = {}, {}, {}
    for major in versions:
        if major == "27":
            continue
        updates, selected, prefixes = fetch_lts(major, configs[major])
        pins.update(updates)
        releases.update(selected)
        overrides.update(prefixes)
        print(f"JDK {major}: " + ", ".join(
            f"{vendor} {release}" for (v, vendor), release in selected.items()))
    planned = {}
    if pins:
        planned[source_file] = replace_source_values(source, releases, overrides)
        path = root / "jdk/catalog.bzl"
        planned[path] = replace_pins(path.read_text(), "REMOTE_JDK_CONFIGS_LIST",
                                    pins, verify_roots)
    if "27" in versions:
        configs27 = fetch_configs("27")
        path = root / "jdk/repositories.bzl"
        updates = {c["name"]: dict(url=c["url"], strip_prefix=c["strip_prefix"],
                                    sha256=c["sha256"]) for c in configs27}
        planned[path] = replace_pins(path.read_text(), "_JDK27_CONFIGS", updates, verify_roots)
        print(f"JDK 27: Zulu {version_of(configs27)}; Temurin per architecture; "
              "Liberica Windows ARM64")
    formatter = shutil.which("buildifier")
    if formatter:
        planned = {path: subprocess.run([formatter, "-type=bzl"], input=text,
                                       capture_output=True, text=True, check=True).stdout
                   for path, text in planned.items()}
    return {path: text for path, text in planned.items() if path.read_text() != text}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    scope = ap.add_mutually_exclusive_group()
    scope.add_argument("--java-version", help="one configured JDK major (default: 27)")
    scope.add_argument("--all", action="store_true", help="refresh all configured LTS and JDK 27 pins")
    ap.add_argument("--dry-run", action="store_true",
                    help="report only; exit 1 if an update is available")
    ap.add_argument("--verify-archive-roots", action="store_true",
                    help="also check each selected archive's root using partial downloads")
    args = ap.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    try:
        configs = ast.literal_eval(assignment(
            (root / "jdk/repositories_util.bzl").read_text(), "_RELEASE_CONFIGS"))
        versions = list(configs) + ["27"] if args.all else [args.java_version or "27"]
        planned = plan_updates(root, versions, args.verify_archive_roots)
        if not planned:
            print("Selected JDK catalogs and generator inputs are up to date.")
            return 0
        for path in planned:
            print(f"Update available: {path.relative_to(root)}")
        if args.dry_run:
            print("No files changed. Run without --dry-run to apply.")
            return 1
        # Fetch and validate every selected vendor before replacing any source file.
        for path, text in planned.items():
            with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as temp:
                staged = Path(temp.name)
                temp.write(text)
            try:
                staged.chmod(path.stat().st_mode & 0o777)
                os.replace(staged, path)
            finally:
                staged.unlink(missing_ok=True)
        print("Updated catalogs and generator inputs. Validate with:")
        print("  bazelisk query //jdk:check_catalog")
        print("Check mirror availability before publishing the LTS pins.")
        return 0
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError,
            tarfile.TarError, struct.error, zlib.error) as error:
        print(f"JDK catalog update failed: {error}", file=sys.stderr)
        if isinstance(error, subprocess.CalledProcessError) and error.stderr:
            print(error.stderr.strip(), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
