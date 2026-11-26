# jdk_catalog

JDK archive pins and toolchains for Bazel, packaged as a standalone Bzlmod module
using upstream [`rules_java`](https://github.com/bazelbuild/rules_java).

This module supplies JDK 25 and 27 directly from its own archive catalogs. It
reuses `rules_java`'s repository and toolchain implementations; neither a
`rules_java` fork nor a separate `java_tools` module is required. Refreshing JDK
pins does not require releasing either of those projects.

## What it provides

- Runtime, bootstrap and compilation toolchains for JDK 25 and 27 across Linux
  (x86_64/aarch64/ppc64le/riscv64/s390x), macOS (x86_64/aarch64), and Windows
  (x86_64/ARM64). Patch versions can differ across architectures.
- `@jdk_catalog//toolchains:remotejdk_25` and `remotejdk_27` — runtime aliases
  for `java_runtime` attributes, using catalog-owned archives.
- `@jdk_catalog//toolchains:toolchain_jdk_25` and `toolchain_jdk_27` — compilation
  toolchains for their respective Java language versions.

## Usage

This module is not yet released or published to the Bazel Central Registry.
For now, add a Git override pinned to a commit whose module name is
`jdk_catalog`:

```starlark
# MODULE.bazel
bazel_dep(name = "rules_java", version = "9.9.0")
bazel_dep(name = "jdk_catalog", version = "0.1.2")
git_override(
    module_name = "jdk_catalog",
    remote = "https://github.com/bazel-contrib/jdk_catalog.git",
    commit = "<catalog-commit>",
)

# Root registrations take precedence over rules_java's bundled JDKs.
register_toolchains("@jdk_catalog//toolchains:all")
```

Replace `<catalog-commit>` with the catalog revision to consume. Registering
from the root is required to prefer this catalog's JDK 25 over upstream
`rules_java`'s JDK 25, and supports restricted non-root registrations.

```
# .bazelrc
build:java25 --java_language_version=25
build:java25 --java_runtime_version=remotejdk_25
build:java25 --tool_java_language_version=25
build:java25 --tool_java_runtime_version=remotejdk_25

build:java27 --java_language_version=27
build:java27 --java_runtime_version=remotejdk_27
build:java27 --tool_java_language_version=27
build:java27 --tool_java_runtime_version=remotejdk_27
```

```
bazelisk build --config=java27 //...
```

After a release is admitted to the BCR, the Git override can be removed.

## Example

`examples/consuming` is a self-contained workspace that consumes this module via
`local_path_override` and builds a Java target at language level 27:

```
cd examples/consuming
bazelisk run --config=java27 //:hello   # prints "Hello from JDK 27"
bazelisk test --config=java27 //:toolchain_test
```

The test checks JDK execution and the corresponding class-file version.
Pass an expected patch version to check it explicitly:

```sh
bazelisk test --config=java25 --test_arg=25.0.5.1 //:toolchain_test
bazelisk test --config=java27 --test_arg=27.0.1.1 //:toolchain_test
```

Without an argument, the test retains its JDK 27 major-version check. The CI workflow covers
Linux x86_64, macOS aarch64, and Windows x86_64 with Bazel 9.3.0, the minimum
supported version.
The remaining catalog architectures are not covered by that workflow.

JDK archives are fetched on demand for selected toolchains; adding the module
does not require downloading every platform's JDK. The configured repository
cache can reuse archives across workspaces.

See the [API reference](docs/README.md), [contributor guide](CONTRIBUTING.md),
and [release procedure](RELEASING.md).

## Updating the catalogs

The [catalog updater](tools/update_jdk_catalog.py) refreshes the configured
JDK 8, 11, 17, 21, 25 and 27 archives from vendor metadata. It updates the
LTS release table and generated pins together, plus the separate JDK 27 pins.
It supports Azul Zulu, Eclipse Temurin, Microsoft OpenJDK and BellSoft Liberica
(JDK 27 on Windows ARM64).

Run from the repository root with Python 3.9+ and `curl`. `buildifier` is
optional; the script uses it when installed.

```sh
# Check for updates without changing files.
python3 tools/update_jdk_catalog.py --all --dry-run

# Apply updates and verify archive root directories using partial downloads.
python3 tools/update_jdk_catalog.py --all --verify-archive-roots

# Check that the LTS pins and their generator inputs agree.
bazelisk query //jdk:check_catalog
```

The dry run exits **0** when current, **1** when updates are available, and
**2** on an error. Checksums come from published vendor metadata; the updater
does not download full JDK archives. Omitting `--verify-archive-roots` skips
the optional layout checks; Microsoft and BellSoft ZIP headers are always
inspected to determine their root directories.

To refresh one release line instead:

```sh
python3 tools/update_jdk_catalog.py --java-version 25 --verify-archive-roots
```

With no scope option, the script retains its original JDK 27-only behavior.
Temurin LTS pins use the newest release available across all configured
architectures for that major. The legacy AdoptOpenJDK 8/s390x entry is retained
and reported explicitly. New platforms or JDK majors still need registration
changes. Review the diff and arrange any missing LTS archive mirroring before
publication; the script does not publish artifacts or modules.

In the three-module split, a JDK pin refresh requires publishing only
`jdk_catalog`: the existing `rules_java` split fork and `java_tools` module
can stay fixed. Consumers using `git_override` must advance their
`jdk_catalog` commit to adopt the refresh. Vanilla upstream `rules_java` does
not consume this external LTS catalog. The
[split consumer example](examples/catalog_split/README.md) demonstrates JDK 25
and 27 compilation and execution with both companion module commits fixed.
See [CONTRIBUTING.md](CONTRIBUTING.md) for updater regression tests and further
validation steps.

## Maintenance and support

David Ostrovsky ([@davido](https://github.com/davido)) and John Cater
([@katre](https://github.com/katre)) maintain this project on a best-effort
volunteer basis; David is the point of contact for the Rules Authors SIG. The
goal is to respond to issues and pull requests within 2–3 weeks; there is no
guaranteed response time or commercial support. Additional maintainers are
welcome.

The catalog follows non-LTS JDK releases, whose vendor maintenance windows are
short. A catalog entry does not extend the vendor's security support. Retiring
public labels follows the versioning policy in [RELEASING.md](RELEASING.md).

## Adding the next non-LTS release

1. Add the archive structs to `jdk/repositories.bzl` (name, `target_compatible_with`,
   `sha256`, `strip_prefix`, `urls`, `version`), mirroring the JDK 27 entries.
2. Add a `remote_jdkNN_repos()` macro and call it from `jdk/extensions.bzl`.
3. List the new repos in `MODULE.bazel` (`use_repo` + `register_toolchains`).
4. Add the `remotejdk_NN` alias and `toolchain_jdk_NN` to `toolchains/BUILD.bazel`.
5. Document the vendor's support window and announce any eventual removal as
   described in [RELEASING.md](RELEASING.md).

## License

Apache License 2.0. See [LICENSE](LICENSE).

## Catalog data and the split prototype

The LTS catalog was originally extracted from rules_java
commit 575fa89. Its Zulu pins now include the November 2026 updates: JDK 8u514,
11.0.33.1, 17.0.21.1, 21.0.13.1 and 25.0.5.1. The separate non-LTS catalog uses
Zulu 27.0.1.1 and preserves the existing JDK 27 toolchains and extension API.
JDK 27 on Windows ARM64 uses BellSoft Liberica 27.0.1.1+5, matching Bazel's
full JDK archive with `jmods`. Windows x86_64 continues to use Zulu.

The Zulu 17, 21, 25 and 27 updates address
[CVE-2026-114938](https://support.azul.com/hc/en-us/articles/55793255806100-Java4Shell-for-Zulu-and-Zing-CVE-2026-114938).
Zulu 8 and 11 are not affected by that issue; their updates are maintenance
refreshes. Temurin LTS pins use the newest release available for every configured
architecture: 11.0.33, 17.0.21.1, 21.0.13.1 and 25.0.5. The Microsoft Windows
ARM64 JDK is 11.0.33.1. The legacy AdoptOpenJDK 8/s390x pin remains at 8u292.
For JDK 27, Temurin ppc64le and s390x use 27.0.1.1; riscv64 remains at 27.0.1.0.2.
These non-x86 architectures are not affected by the AVX-512 vulnerability.

`jdk/catalog.bzl` owns pins; `jdk/repositories_util.bzl` owns version and URL
construction. `bazelisk query //jdk:check_catalog` checks their agreement without
downloads. `bazelisk build //jdk:catalog_manifest` exports the selected pins.

Use the [catalog updater](#updating-the-catalogs) to refresh the LTS and non-LTS
pins together from vendor metadata.

Alternatively, regenerate LTS entries with
`bazelisk build //jdk:dump_remote_jdk_configs`, then
replace the struct entries in `jdk/catalog.bzl` with the generated output and
rerun the check. Regeneration downloads all configured JDK archives; it is a
maintainer operation, not a build prerequisite. Do not run it merely to check
the catalog. The original rules_java generator label forwards here.

The JDK 25 extension reads `jdk/catalog.bzl` directly, so ordinary consumers
use upstream `rules_java` and need no split prototype. The other LTS majors
remain pin data for the optional catalog-split prototype, whose `rules_java`
fork reads this catalog through a normal module dependency.
Module dependency cycles are supported by Bzlmod: this module continues using
rules_java's toolchain APIs while its pure catalog file has no loads back into
rules_java. All prototype consumers must pin the fork using a git override.
