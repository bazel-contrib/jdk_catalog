# Contributing

Open an issue to discuss a new JDK release, platform, or change to the public
toolchain labels. Small fixes can go directly into a pull request.

Keep this module focused on non-LTS JDK catalogs and reuse `rules_java`'s
toolchain machinery. Include the JDK vendor, download URLs, archive layout,
and verified SHA-256 checksums when updating the catalog. Do not download every
platform archive just to run a local smoke test.

Use [Bazelisk](https://github.com/bazelbuild/bazelisk) and the checked-in Bazel
version. From the repository root, build the API documentation:

```sh
bazelisk build //docs:extensions //docs:repositories
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
