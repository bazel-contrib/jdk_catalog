# API reference

Consumers add a `bazel_dep`, register `@jdk_catalog//toolchains:all` in their
root module and select Java 25 or 27 using the flags in the
[README](../README.md). Root registration prefers catalog JDKs over the JDKs
bundled with upstream `rules_java`. No fork of the rules or tools is required.

Public labels:

| Label | Purpose |
| --- | --- |
| `@jdk_catalog//toolchains:remotejdk_25` | Java 25 runtime alias using catalog-owned archives. |
| `@jdk_catalog//toolchains:remotejdk_27` | Java 27 runtime alias for `java_runtime` attributes. |
| `@jdk_catalog//toolchains:toolchain_jdk_25` | Java 25 compilation toolchain. |
| `@jdk_catalog//toolchains:toolchain_jdk_27` | Java 27 compilation toolchain. |

The `@jdk_catalog//jdk:extensions.bzl%jdks` extension provides JDK 25 and 27
archives and runtime configuration repositories. It uses `remote_jdk25_repos()`
and `remote_jdk27_repos()`. Consumers normally do not call these directly.
The older `non_lts_jdks` extension remains available for direct users of JDK 27.

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
this directory. Check the snapshots with `python3 tools/check_api_docs.py`
from the repository root. CI uses this checker with the pinned Bazel version.
