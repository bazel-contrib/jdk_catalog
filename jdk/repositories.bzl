# Copyright 2026 The Bazel Authors. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Remote JDK repositories for JDK 25 and 27.

These reuse rules_java's remote_java_repository macro to import the JDK archive
and generate the runtime toolchain definitions; this module only carries the
catalog of archives.
"""

load("@bazel_tools//tools/build_defs/repo:utils.bzl", "maybe")
load("@rules_java//toolchains:remote_java_repository.bzl", "remote_java_repository")
load(":catalog.bzl", "REMOTE_JDK_CONFIGS_LIST")

JDK25_CONFIGS = [cfg for cfg in REMOTE_JDK_CONFIGS_LIST if cfg.version == "25"]

# Zulu Community builds (linux/macos/windows) plus Adoptium Temurin for the
# architectures Azul does not publish (ppc64le, riscv64, s390x).
_JDK27_CONFIGS = [
    struct(
        name = "remotejdk27_linux",
        target_compatible_with = ["@platforms//os:linux", "@platforms//cpu:x86_64"],
        sha256 = "c4d7bf4c80a21e935187ecdcb111e4b2f14e1fdd18364974fe7f7da54b12bea0",
        strip_prefix = "zulu27.30.201-ca-jdk27.0.1.1-linux_x64",
        urls = [
            "https://cdn.azul.com/zulu/bin/zulu27.30.201-ca-jdk27.0.1.1-linux_x64.tar.gz",
        ],
        version = "27",
    ),
    struct(
        name = "remotejdk27_linux_aarch64",
        target_compatible_with = ["@platforms//os:linux", "@platforms//cpu:aarch64"],
        sha256 = "18875b92ad2535230a13175f718933f7cc0593b4affa2dab442815ec245dacbb",
        strip_prefix = "zulu27.30.201-ca-jdk27.0.1.1-linux_aarch64",
        urls = [
            "https://cdn.azul.com/zulu/bin/zulu27.30.201-ca-jdk27.0.1.1-linux_aarch64.tar.gz",
        ],
        version = "27",
    ),
    struct(
        name = "remotejdk27_macos",
        target_compatible_with = ["@platforms//os:macos", "@platforms//cpu:x86_64"],
        sha256 = "271f8d1bb2f692bdc981799e8f251133c854cc5c1edafa80298a461bb8909dec",
        strip_prefix = "zulu27.30.201-ca-jdk27.0.1.1-macosx_x64",
        urls = [
            "https://cdn.azul.com/zulu/bin/zulu27.30.201-ca-jdk27.0.1.1-macosx_x64.tar.gz",
        ],
        version = "27",
        patch_cmds = ["ln -s Contents/Home/* ."],
    ),
    struct(
        name = "remotejdk27_macos_aarch64",
        target_compatible_with = ["@platforms//os:macos", "@platforms//cpu:aarch64"],
        sha256 = "1d28430a13d257248856792e0131d845cbe324145971df7c9716ec2a92ac0fca",
        strip_prefix = "zulu27.30.201-ca-jdk27.0.1.1-macosx_aarch64",
        urls = [
            "https://cdn.azul.com/zulu/bin/zulu27.30.201-ca-jdk27.0.1.1-macosx_aarch64.tar.gz",
        ],
        version = "27",
        patch_cmds = ["ln -s Contents/Home/* ."],
    ),
    struct(
        name = "remotejdk27_win",
        target_compatible_with = ["@platforms//os:windows", "@platforms//cpu:x86_64"],
        sha256 = "f5424ea36f832aa28a0441a57ffb1dfe2cd3d903802c0a36d22576b1acc430ec",
        strip_prefix = "zulu27.30.201-ca-jdk27.0.1.1-win_x64",
        urls = [
            "https://cdn.azul.com/zulu/bin/zulu27.30.201-ca-jdk27.0.1.1-win_x64.zip",
        ],
        version = "27",
    ),
    # Liberica's full Windows ARM64 JDK includes jmods, as required by Bazel's
    # embedded-JDK cross-jlink build. Keep the same archive/provider here.
    struct(
        name = "remotejdk27_win_arm64",
        target_compatible_with = ["@platforms//os:windows", "@platforms//cpu:arm64"],
        sha256 = "3f4273f9ecea9ba17ce3d7463cb55cab4446ff1cea25e3577574cc8a6449d245",
        strip_prefix = "jdk-27.0.1.1",
        urls = [
            "https://github.com/bell-sw/Liberica/releases/download/27.0.1.1%2B5/bellsoft-jdk27.0.1.1%2B5-windows-aarch64.zip",
        ],
        version = "27",
    ),
    struct(
        name = "remotejdk27_linux_ppc64le",
        target_compatible_with = ["@platforms//os:linux", "@platforms//cpu:ppc64le"],
        sha256 = "7250ecc091b6b4020918dc084b3ad0ee5e7bd136a52ee9a29e85954147ebb694",
        strip_prefix = "jdk-27.0.1.1+4",
        urls = [
            "https://github.com/adoptium/temurin27-binaries/releases/download/jdk-27.0.1.1+4/OpenJDK27U-jdk_ppc64le_linux_hotspot_27.0.1.1_4.tar.gz",
        ],
        version = "27",
    ),
    struct(
        name = "remotejdk27_linux_riscv64",
        target_compatible_with = ["@platforms//os:linux", "@platforms//cpu:riscv64"],
        sha256 = "8d03b2a87e5a9acf19b84d45d1195064656bbb17c5381a060d8d0ba7a3f409ed",
        strip_prefix = "jdk-27.0.1.1+4",
        urls = [
            "https://github.com/adoptium/temurin27-binaries/releases/download/jdk-27.0.1.1+4/OpenJDK27U-jdk_riscv64_linux_hotspot_27.0.1.1_4.tar.gz",
        ],
        version = "27",
    ),
    struct(
        name = "remotejdk27_linux_s390x",
        target_compatible_with = ["@platforms//os:linux", "@platforms//cpu:s390x"],
        sha256 = "32950ee8da75cb0472b3c77f3559384ecf2740652c664a9db0f24c3423c0a79f",
        strip_prefix = "jdk-27.0.1.1+4",
        urls = [
            "https://github.com/adoptium/temurin27-binaries/releases/download/jdk-27.0.1.1+4/OpenJDK27U-jdk_s390x_linux_hotspot_27.0.1.1_4.tar.gz",
        ],
        version = "27",
    ),
]

JDK27_CONFIGS = _JDK27_CONFIGS

def remote_jdk25_repos():
    """Imports JDK 25 archives from this module's LTS catalog."""
    _remote_jdk_repos(JDK25_CONFIGS)

def remote_jdk27_repos():
    """Imports the OpenJDK 27 archives and their runtime toolchain definitions."""
    _remote_jdk_repos(JDK27_CONFIGS)

def _remote_jdk_repos(configs):
    for item in configs:
        maybe(
            remote_java_repository,
            name = item.name,
            target_compatible_with = item.target_compatible_with,
            sha256 = item.sha256,
            strip_prefix = item.strip_prefix,
            urls = item.urls,
            version = item.version,
            patch_cmds = getattr(item, "patch_cmds", []),
        )
