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

"""Module extension that instantiates the non-LTS remote JDK repositories."""

load("//jdk:repositories.bzl", "remote_jdk27_repos")

def _non_lts_jdks_impl(module_ctx):
    remote_jdk27_repos()
    return module_ctx.extension_metadata(reproducible = True)

non_lts_jdks = module_extension(
    implementation = _non_lts_jdks_impl,
    doc = """Provides the non-LTS JDK archive and runtime-configuration repositories.

The jdk_catalog module uses this extension and registers the runtime and
compilation toolchains automatically. Consumers normally need only bazel_dep;
they do not need to call use_extension or register_toolchains themselves.

Archives are fetched on demand when their toolchains are selected. There are no
configuration tags. JDK 27 currently covers Linux x86_64, aarch64, ppc64le,
riscv64 and s390x; macOS x86_64 and aarch64; and Windows x86_64 and ARM64.
""",
)
