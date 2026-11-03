# Copyright 2019 The Bazel Authors. All rights reserved.
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

"""Validate the pinned catalog against its version/URL source of truth."""

load(":catalog.bzl", "REMOTE_JDK_CONFIGS_LIST")
load(":repositories_util.bzl", "FLAT_CONFIGS")

def validate_configs(configs = REMOTE_JDK_CONFIGS_LIST):
    """Fail during loading if a catalog entry and its generator disagree."""
    actual = {cfg.name: cfg for cfg in configs}
    if len(actual) != len(configs):
        fail("duplicate JDK names in catalog")
    expected = {cfg.name: cfg for cfg in FLAT_CONFIGS}
    if sorted(actual.keys()) != sorted(expected.keys()):
        fail("JDK catalog names disagree with generator")
    for name, source in expected.items():
        cfg = actual[name]
        for field in ["version", "urls", "strip_prefix", "target_compatible_with", "patch_cmds"]:
            if getattr(cfg, field, []) != getattr(source, field, []):
                fail("JDK catalog mismatch for {}: {}".format(name, field))
        if len(cfg.sha256) != 64:
            fail("expected a SHA-256 checksum for " + name)
        for character in cfg.sha256.elems():
            if character not in "0123456789abcdef":
                fail("invalid SHA-256 checksum for " + name)
