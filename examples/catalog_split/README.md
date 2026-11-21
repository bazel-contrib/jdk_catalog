# Verify an independent JDK catalog refresh

This consumer fixes `rules_java` and `java_tools` to published split-prototype
commits on GitHub and selects only `jdk_catalog` from this checkout. Its test
checks the actual runtime patch version and the compiler's class-file version.

From this directory, verify the November 2026 catalog on the current host:

```sh
bazelisk test //:runtime_test \
  --java_language_version=25 --java_runtime_version=remotejdk_25 \
  --tool_java_language_version=25 --tool_java_runtime_version=remotejdk_25 \
  --test_arg=25.0.5.1 --cache_test_results=no --test_output=all --lockfile_mode=off

bazelisk test //:runtime_test \
  --java_language_version=27 --java_runtime_version=remotejdk_27 \
  --tool_java_language_version=27 --tool_java_runtime_version=remotejdk_27 \
  --test_arg=27.0.1.1 --cache_test_results=no --test_output=all --lockfile_mode=off
```

The commands pass on macOS x86-64 with Bazel 9.3.0. They compile Java code and
execute the test with the selected JDK; they do not establish compatibility
on other platforms or remote execution. The tools module is a personal
snapshot, not an official java_tools v23 release.

Only `jdk_catalog` needs a new published commit for this refresh. A consumer
using a pinned `git_override` must then advance that catalog commit. The two
other module source commits remain fixed. To test a published catalog here,
replace its `local_path_override` with a `git_override` for the desired commit.

The upstream pin-refresh work in `rules_java` is separate from this split:
unmodified upstream rules_java does not read this external LTS catalog.
