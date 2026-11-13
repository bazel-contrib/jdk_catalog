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

"""Remote JDK repositories for non-LTS releases (currently JDK 27).

These reuse rules_java's remote_java_repository macro to import the JDK archive
and generate the runtime toolchain definitions; this module only carries the
catalog of archives.
"""

load("@bazel_tools//tools/build_defs/repo:utils.bzl", "maybe")
load("@rules_java//toolchains:remote_java_repository.bzl", "remote_java_repository")

# Zulu Community builds (linux/macos/windows) plus Adoptium Temurin for the
# architectures Azul does not publish (ppc64le, riscv64, s390x).
_JDK27_CONFIGS = [
    struct(
        name = "remotejdk27_linux",
        target_compatible_with = ["@platforms//os:linux", "@platforms//cpu:x86_64"],
        sha256 = "c128817926e4eebb30868b6ba082028f493afa716e459e34049bde0ab49a9829",
        strip_prefix = "zulu27.30.109-ca-jdk27.0.1.0.3-linux_x64",
        urls = [
            "https://cdn.azul.com/zulu/bin/zulu27.30.109-ca-jdk27.0.1.0.3-linux_x64.tar.gz",
        ],
        version = "27",
    ),
    struct(
        name = "remotejdk27_linux_aarch64",
        target_compatible_with = ["@platforms//os:linux", "@platforms//cpu:aarch64"],
        sha256 = "4b4d2fb4a6bff5fa4d3a1f22ac5933c87d83e41d5f78bcd88df878326342d507",
        strip_prefix = "zulu27.30.109-ca-jdk27.0.1.0.3-linux_aarch64",
        urls = [
            "https://cdn.azul.com/zulu/bin/zulu27.30.109-ca-jdk27.0.1.0.3-linux_aarch64.tar.gz",
        ],
        version = "27",
    ),
    struct(
        name = "remotejdk27_macos",
        target_compatible_with = ["@platforms//os:macos", "@platforms//cpu:x86_64"],
        sha256 = "88cf4b1d04ed677d88e53716fb0c960b89917a0234cea6555ba9aa5d37961b83",
        strip_prefix = "zulu27.30.109-ca-jdk27.0.1.0.3-macosx_x64",
        urls = [
            "https://cdn.azul.com/zulu/bin/zulu27.30.109-ca-jdk27.0.1.0.3-macosx_x64.tar.gz",
        ],
        version = "27",
        patch_cmds = ["ln -s Contents/Home/* ."],
    ),
    struct(
        name = "remotejdk27_macos_aarch64",
        target_compatible_with = ["@platforms//os:macos", "@platforms//cpu:aarch64"],
        sha256 = "88dec2f8609e7c4162778cbaef5437f00febd3c498a7c0e77277d1f4ac8f839d",
        strip_prefix = "zulu27.30.109-ca-jdk27.0.1.0.3-macosx_aarch64",
        urls = [
            "https://cdn.azul.com/zulu/bin/zulu27.30.109-ca-jdk27.0.1.0.3-macosx_aarch64.tar.gz",
        ],
        version = "27",
        patch_cmds = ["ln -s Contents/Home/* ."],
    ),
    struct(
        name = "remotejdk27_win",
        target_compatible_with = ["@platforms//os:windows", "@platforms//cpu:x86_64"],
        sha256 = "70e0aff2bfc1a9468ef464f97c96b295188c15f5a6f7fec3429a4b924b8b338d",
        strip_prefix = "zulu27.30.109-ca-jdk27.0.1.0.3-win_x64",
        urls = [
            "https://cdn.azul.com/zulu/bin/zulu27.30.109-ca-jdk27.0.1.0.3-win_x64.zip",
        ],
        version = "27",
    ),
    struct(
        name = "remotejdk27_linux_ppc64le",
        target_compatible_with = ["@platforms//os:linux", "@platforms//cpu:ppc64le"],
        sha256 = "c0fd2832050eb3320334c8ee0d620ead55651059fd29d41a185d92a459e43fc2",
        strip_prefix = "jdk-27.0.1.0.2+1",
        urls = [
            "https://github.com/adoptium/temurin27-binaries/releases/download/jdk-27.0.1.0.2+1/OpenJDK27U-jdk_ppc64le_linux_hotspot_27.0.1.0.2_1.tar.gz",
        ],
        version = "27",
    ),
    struct(
        name = "remotejdk27_linux_riscv64",
        target_compatible_with = ["@platforms//os:linux", "@platforms//cpu:riscv64"],
        sha256 = "e788df9ad7db79a2356539a170d09340d0fc354412ce23881eef6c6339928ce2",
        strip_prefix = "jdk-27.0.1.0.2+1",
        urls = [
            "https://github.com/adoptium/temurin27-binaries/releases/download/jdk-27.0.1.0.2+1/OpenJDK27U-jdk_riscv64_linux_hotspot_27.0.1.0.2_1.tar.gz",
        ],
        version = "27",
    ),
    struct(
        name = "remotejdk27_linux_s390x",
        target_compatible_with = ["@platforms//os:linux", "@platforms//cpu:s390x"],
        sha256 = "6c4e1f13490f1efb38b5f52667f05c433f7c94ae59c7e307a193e94b7b597e26",
        strip_prefix = "jdk-27.0.1.0.2+1",
        urls = [
            "https://github.com/adoptium/temurin27-binaries/releases/download/jdk-27.0.1.0.2+1/OpenJDK27U-jdk_s390x_linux_hotspot_27.0.1.0.2_1.tar.gz",
        ],
        version = "27",
    ),
]

def remote_jdk27_repos():
    """Imports the OpenJDK 27 archives and their runtime toolchain definitions."""
    for item in _JDK27_CONFIGS:
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
