# API reference

Normal consumers add a `bazel_dep` and select Java 27 using the flags in the
[README](../README.md). The module registers its toolchains automatically.

Public labels:

| Label | Purpose |
| --- | --- |
| `@java_toolchains//toolchains:remotejdk_27` | Java runtime alias for `java_runtime` attributes. |
| `@java_toolchains//toolchains:toolchain_jdk_27` | Java 27 compilation toolchain. |

The Starlark extension `@java_toolchains//jdk:extensions.bzl%non_lts_jdks`
provides the platform archives and runtime configuration repositories. Its
`remote_jdk27_repos()` implementation helper is also documented for maintainers;
consumers do not normally call it directly.

Checked-in generated references: [extension](extensions.textproto) and
[repository macro](repositories.textproto).

Generate the API reference from the actual Starlark definitions:

```sh
bazelisk build //docs:extensions //docs:repositories \
  //docs:extensions.textproto //docs:repositories.textproto
```

Outputs are under `bazel-bin/docs/`. The `.textproto` files are readable locally;
the `.binaryproto` files use the standard Stardoc `ModuleInfo` format that the
[BCR can render](https://github.com/bazelbuild/bazel-central-registry/blob/main/docs/stardoc.md).
This uses Bazel's built-in extractor and adds no documentation dependencies.
After editing public docstrings, copy the generated `.textproto` outputs to
this directory. CI checks those snapshots using the pinned Bazel version.
