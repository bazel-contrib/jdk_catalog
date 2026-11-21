# Contributing

Open an issue to discuss a new JDK release, platform, or change to the public
toolchain labels. Small fixes can go directly into a pull request.

Keep this module focused on non-LTS JDK catalogs and reuse `rules_java`'s
toolchain machinery. Include the JDK vendor, download URLs, archive layout,
and verified SHA-256 checksums when updating the catalog. Do not download every
platform archive just to run a local smoke test.

Refresh all configured catalogs and their generator inputs with Python 3.9+
and `curl`:

```sh
python3 tools/update_jdk_catalog.py --all --dry-run
python3 tools/update_jdk_catalog.py --all --verify-archive-roots
bazelisk query //jdk:check_catalog
```

The dry run exits 0 when current, 1 when an update is available, and 2 on an
error. It changes no files. The updater fetches and validates the selected
vendor metadata before writing any catalog. `--verify-archive-roots` checks
archive roots using small partial downloads; full JDK archives are not needed.
Checksums come from the vendors' published metadata. Microsoft archive headers
are always inspected because their root directories include a build number
absent from their filenames. `buildifier` runs when installed.
JDK 27 on Windows ARM64 uses BellSoft's full Liberica JDK. Its version comes
from BellSoft's discovery API, its SHA-256 from the published GitHub release
asset metadata, and its archive root is checked from the ZIP header.

`--all` refreshes `jdk/catalog.bzl`, its release/URL source in
`jdk/repositories_util.bzl`, and the non-LTS pins in `jdk/repositories.bzl`.
Use `--java-version 25` to select one LTS line. With no scope option, the
script retains its original JDK 27-only behavior.

Temurin LTS updates select the newest GA release available across every
configured architecture for that major. The non-LTS catalog can select
different releases per architecture. The legacy AdoptOpenJDK 8/s390x entry is
retained and reported explicitly. Adding a vendor, platform or JDK major still
requires a code change. LTS mirror URLs follow the existing generator policy;
check availability and arrange mirroring before publication.

Run the updater's offline regression tests with:

```sh
python3 -B -m unittest discover -s tools -p 'update_jdk_catalog_test.py'
```

This updates only `jdk_catalog`. The split installation's `rules_java` and
`java_tools` modules do not need a release for a catalog pin refresh. Consumers
using a pinned `git_override` must advance the `jdk_catalog` commit to adopt it.

Use [Bazelisk](https://github.com/bazelbuild/bazelisk) and the checked-in Bazel
version. From the repository root, build the API documentation:

```sh
bazelisk build //docs:extensions //docs:repositories
python3 tools/check_api_docs.py
```

Run the integration test in the separate consuming module:

```sh
cd examples/consuming
bazelisk test --config=java27 --test_output=errors //:toolchain_test
bazelisk test --config=java27 --java_runtime_version=27 --test_output=errors //:toolchain_test
bazelisk run --config=java27 //:hello
```

The test verifies both JDK 27 execution and Java 27 class-file output. CI runs
these commands on Linux, macOS, and Windows with Bazel 9.3.0. Other
catalog architectures need validation on corresponding hosts or remote workers.

Format Starlark files using `buildifier`. Keep generated documentation in sync
when changing public docstrings; see [docs/README.md](docs/README.md). Use clear
commit messages describing the reason for a change. Contributions are licensed
under this repository's Apache-2.0 license.
