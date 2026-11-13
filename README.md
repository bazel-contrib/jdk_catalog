# jdk_catalog

Non-LTS JDK toolchains for Bazel, packaged as a standalone bzlmod module on top
of [`rules_java`](https://github.com/bazelbuild/rules_java).

`rules_java` ships remote JDK toolchains for the LTS line (8, 11, 17, 21, 25) and
is deliberately conservative about carrying non-LTS releases, since each one is
only supported for six months. This module adds those short-lived releases
(currently **JDK 27**) without forking `rules_java`: it reuses `rules_java`'s own
`remote_java_repository`, `default_java_toolchain`, and `java_runtime_version_alias`
machinery and only contributes the archive catalog.

## What it provides

- Runtime toolchains for JDK 27 across linux (x86_64/aarch64/ppc64le/riscv64/s390x),
  macOS (x86_64/aarch64), and Windows (x86_64), selectable with
  `--java_runtime_version=remotejdk_27` (or `=27`).
- `@jdk_catalog//toolchains:remotejdk_27` — the runtime label, for use
  as a `java_runtime = ...` attribute.
- `@jdk_catalog//toolchains:toolchain_jdk_27` — a compile toolchain that
  runs `javac` on JDK 27, selectable with `--java_language_version=27`. (The LTS
  toolchains top out at JDK 25, whose `javac` rejects source/target 27.)

## Usage

This module is not yet released or published to the Bazel Central Registry.
For now, add a Git override pinned to a commit whose module name is
`jdk_catalog`:

```starlark
# MODULE.bazel
bazel_dep(name = "rules_java", version = "9.9.0")
bazel_dep(name = "jdk_catalog", version = "0.0.1")
git_override(
    module_name = "jdk_catalog",
    remote = "https://github.com/davido/jdk_catalog.git",
    commit = "5ba7b4f08019bccab1f560f29d1734ed55e3e985",
)
```

```
# .bazelrc
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

The test checks JDK 27 execution and Java 27 bytecode. The CI workflow covers
Linux x86_64, macOS aarch64, and Windows x86_64 with Bazel 9.3.0, the minimum
supported version.
The remaining catalog architectures are not covered by that workflow.

JDK archives are fetched on demand for selected toolchains; adding the module
does not require downloading every platform's JDK. The configured repository
cache can reuse archives across workspaces.

See the [API reference](docs/README.md), [contributor guide](CONTRIBUTING.md),
and [release procedure](RELEASING.md).

## Maintenance and support

David Ostrovsky ([@davido](https://github.com/davido)) maintains this project
on a best-effort volunteer basis and is the point of contact for the Rules
Authors SIG. The goal is to respond to issues and pull requests within
2–3 weeks; there is no guaranteed response time or commercial support.
Additional maintainers are welcome.

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

## LTS catalog extraction prototype

This branch also provides the LTS catalog extracted from rules_java HEAD
575fa89, including fmeum's JDK 25.0.5 refresh. The existing JDK 27 toolchains
and extension API remain available.

`jdk/catalog.bzl` owns pins; `jdk/repositories_util.bzl` owns version and URL
construction. `bazelisk query //jdk:check_catalog` checks their agreement without
downloads. `bazelisk build //jdk:catalog_manifest` exports the selected pins.

Regenerate entries with `bazelisk build //jdk:dump_remote_jdk_configs`, then
replace the struct entries in `jdk/catalog.bzl` with the generated output and
rerun the check. Regeneration downloads all configured JDK archives; it is a
maintainer operation, not a build prerequisite. Do not run it merely to check
the catalog. The original rules_java generator label forwards here.

The rules_java fork reads this catalog through a normal module dependency.
Module dependency cycles are supported by Bzlmod: this module continues using
rules_java's toolchain APIs while its pure catalog file has no loads back into
rules_java. All prototype consumers must pin the fork using a git override.
