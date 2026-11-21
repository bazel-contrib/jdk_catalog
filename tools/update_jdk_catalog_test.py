# Copyright 2026 The Bazel Authors. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import update_jdk_catalog as updater


SOURCE = '''visibility("public")
# Keep this historical version in the comment: 17.70.111-ca-jdk17.0.21.
_RELEASE_CONFIGS = {
    "17": {
        "zulu": {
            "release": "17.70.111-ca-jdk17.0.21",
            "platforms": {"macos": ["x86_64"]},
        },
    },
    "25": {},
}
_STRIP_PREFIX_OVERRIDES = {"remotejdk11_win_arm64": "jdk-11.0.32+9"}
'''

PINS = '''REMOTE_JDK_CONFIGS_LIST = [
    struct(
        name = "remotejdk17_macos",
        sha256 = "''' + "a" * 64 + '''",
        strip_prefix = "old",
        urls = ["https://example.test/old", "https://mirror.bazel.build/old"],
        version = "17",
        target_compatible_with = ["@platforms//os:macos", "@platforms//cpu:x86_64"],
        patch_cmds = ["ln -s Contents/Home/* ."],
    ),
]
'''


class UpdateJdkCatalogTest(unittest.TestCase):
    def test_non_lts_pins_module_imports_and_toolchains_cover_same_platforms(self):
        root = Path(__file__).resolve().parents[1]
        pins = updater.assignment((root / "jdk/repositories.bzl").read_text(), "_JDK27_CONFIGS")
        pin_names = {next(updater.ast.literal_eval(k.value) for k in pin.keywords
                          if k.arg == "name") for pin in pins.elts}
        imported = updater.ast.literal_eval(updater.assignment(
            (root / "MODULE.bazel").read_text(), "_REMOTE_JDK27_REPOS"))
        runtimes = dict(updater.ast.literal_eval(updater.assignment(
            (root / "toolchains/BUILD.bazel").read_text(), "_JDK27_RUNTIMES")))
        self.assertEqual(pin_names, set(imported))
        self.assertEqual(pin_names, runtimes.keys())
        self.assertEqual(runtimes["remotejdk27_win_arm64"],
                         ["@platforms//os:windows", "@platforms//cpu:arm64"])

    def test_bellsoft_uses_full_ga_jdk_and_published_sha256(self):
        builds = [
            {"GA": True, "bundleType": "jdk-lite", "featureVersion": 27},
            {"GA": False, "bundleType": "jdk", "featureVersion": 27},
            {"GA": True, "bundleType": "jdk", "featureVersion": 27,
             "version": "27.0.1.1+5", "filename": "bellsoft-jdk27-win-arm64.zip"},
        ]
        release = {"assets": [{"name": "bellsoft-jdk27-win-arm64.zip",
                               "browser_download_url": "https://example.test/jdk.zip",
                               "digest": "sha256:" + "b" * 64}]}
        with (patch.object(updater, "curl_json", side_effect=[builds, release]),
              patch.object(updater, "archive_root", return_value="jdk-27.0.1.1")):
            self.assertEqual(updater.bellsoft_build("27"),
                             ("https://example.test/jdk.zip", "jdk-27.0.1.1", "b" * 64))

    def test_bellsoft_requires_sha256_not_sha1(self):
        builds = [{"GA": True, "bundleType": "jdk", "featureVersion": 27,
                   "version": "27.0.1.1+5", "filename": "jdk.zip"}]
        release = {"assets": [{"name": "jdk.zip", "digest": "sha1:" + "a" * 40}]}
        with patch.object(updater, "curl_json", side_effect=[builds, release]):
            with self.assertRaisesRegex(ValueError, "Missing published SHA-256"):
                updater.bellsoft_build("27")

    def test_common_release_waits_for_all_configured_architectures(self):
        releases = [
            {"release_name": "jdk-25.0.5.1+2", "binaries": [{"architecture": "ppc64le"}]},
            {"release_name": "jdk-25.0.5+8", "binaries": [
                {"architecture": "ppc64le"}, {"architecture": "riscv64"}]},
        ]
        with patch.object(updater, "curl_json", return_value=releases):
            release, binaries = updater.common_temurin_release("25", ["ppc64le", "riscv64"])
        self.assertEqual(release, "jdk-25.0.5+8")
        self.assertEqual(set(binaries), {"ppc64le", "riscv64"})

    def test_missing_common_release_is_an_error(self):
        releases = [{"release_name": "jdk-25.0.5.1+2", "binaries": [{"architecture": "ppc64le"}]}]
        with patch.object(updater, "curl_json", return_value=releases):
            with self.assertRaisesRegex(ValueError, "No common Temurin"):
                updater.common_temurin_release("25", ["ppc64le", "riscv64"])

    def test_generator_update_preserves_comments_and_platforms(self):
        result = updater.replace_source_values(
            SOURCE, {("17", "zulu"): "17.70.201-ca-jdk17.0.21.1"},
            {"remotejdk11_win_arm64": "jdk-11.0.33.1+1"})
        self.assertIn("historical version in the comment: 17.70.111-ca-jdk17.0.21", result)
        self.assertIn('"release": "17.70.201-ca-jdk17.0.21.1"', result)
        self.assertIn('"platforms": {"macos": ["x86_64"]}', result)
        self.assertIn('"jdk-11.0.33.1+1"', result)

    def test_pin_update_preserves_mac_layout_and_major_selector(self):
        updates = {"remotejdk17_macos": dict(
            url="https://example.test/new", strip_prefix="new", sha256="b" * 64)}
        result = updater.replace_pins(PINS, "REMOTE_JDK_CONFIGS_LIST", updates)
        self.assertIn('patch_cmds = ["ln -s Contents/Home/* ."]', result)
        self.assertIn('version = "17"', result)
        self.assertIn('"https://mirror.bazel.build/example.test/new"', result)
        self.assertEqual(result, updater.replace_pins(result, "REMOTE_JDK_CONFIGS_LIST", updates))

    def test_invalid_checksum_is_rejected(self):
        updates = {"remotejdk17_macos": dict(url="https://example.test/new",
                                            strip_prefix="new", sha256="bad")}
        with self.assertRaisesRegex(ValueError, "Invalid vendor SHA-256"):
            updater.replace_pins(PINS, "REMOTE_JDK_CONFIGS_LIST", updates)

    def test_archive_root_mismatch_is_rejected(self):
        updates = {"remotejdk17_macos": dict(url="https://example.test/new.tar.gz",
                                            strip_prefix="new", sha256="b" * 64)}
        with patch.object(updater, "archive_root", return_value="unexpected"):
            with self.assertRaisesRegex(ValueError, "Archive root mismatch"):
                updater.replace_pins(PINS, "REMOTE_JDK_CONFIGS_LIST", updates, True)

    def test_new_unregistered_platform_is_rejected(self):
        updates = {"remotejdk17_new_platform": dict(url="https://example.test/new",
                                                   strip_prefix="new", sha256="b" * 64)}
        with self.assertRaisesRegex(ValueError, "unregistered JDK repositories"):
            updater.replace_pins(PINS, "REMOTE_JDK_CONFIGS_LIST", updates)

    def test_dry_run_selects_all_versions_and_changes_no_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            (root / "jdk").mkdir()
            source = root / "jdk/repositories_util.bzl"
            source.write_text(SOURCE)
            with (patch.object(updater, "__file__", str(root / "tools/updater.py")),
                  patch.object(updater, "plan_updates", return_value={source: "changed"}) as plan,
                  patch("sys.stdout", new_callable=io.StringIO)):
                self.assertEqual(updater.main(["--all", "--dry-run"]), 1)
            plan.assert_called_once_with(root, ["17", "25", "27"], False)
            self.assertEqual(source.read_text(), SOURCE)

    def test_later_vendor_failure_leaves_all_files_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            (root / "jdk").mkdir()
            source = root / "jdk/repositories_util.bzl"
            source.write_text(SOURCE)
            with (patch.object(updater, "__file__", str(root / "tools/updater.py")),
                  patch.object(updater, "fetch_lts", side_effect=[({}, {}, {}), ValueError("vendor offline")]),
                  patch("sys.stdout", new_callable=io.StringIO),
                  patch("sys.stderr", new_callable=io.StringIO)):
                self.assertEqual(updater.main(["--all"]), 2)
            self.assertEqual(source.read_text(), SOURCE)
            self.assertEqual(list((root / "jdk").iterdir()), [source])


if __name__ == "__main__":
    unittest.main()
