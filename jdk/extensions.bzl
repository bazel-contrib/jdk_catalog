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

"""Module extensions that instantiate catalog-owned JDK repositories."""

load("//jdk:repositories.bzl", "remote_jdk25_repos", "remote_jdk27_repos")

def _jdks_impl(module_ctx):
    remote_jdk25_repos()
    remote_jdk27_repos()
    return module_ctx.extension_metadata(reproducible = True)

jdks = module_extension(
    implementation = _jdks_impl,
    doc = """Provides JDK 25 and 27 archive and runtime-configuration repositories.

The jdk_catalog module uses this extension internally. Consumers register
@jdk_catalog//toolchains:all in their root module to prefer these JDKs over
rules_java's bundled runtime registrations. The rules_java implementation and
java_tools release do not need to change when catalog pins are refreshed.

Archives are fetched on demand. There are no configuration tags. Both versions
cover Linux x86_64, aarch64, ppc64le, riscv64 and s390x; macOS x86_64 and aarch64;
and Windows x86_64 and ARM64. Patch versions can differ across architectures.
""",
)

def _non_lts_jdks_impl(module_ctx):
    remote_jdk27_repos()
    return module_ctx.extension_metadata(reproducible = True)

non_lts_jdks = module_extension(
    implementation = _non_lts_jdks_impl,
    doc = """Compatibility extension providing only JDK 27 repositories.

Existing direct users can retain this extension. The jdk_catalog module now
uses jdks internally to supply both JDK 25 and 27. Repositories are fetched on
demand and no configuration tags are supported.
""",
)
