#!/usr/bin/env bash

# Adapted from rules_java's release preparation convention.
set -o errexit -o nounset -o pipefail

release_tag="${1:?Usage: release_prep.sh v<version>}"
if [[ ! "$release_tag" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "Expected a stable semver tag such as v0.0.1" >&2
  exit 1
fi
if [[ "$(git rev-parse HEAD)" != "$(git rev-parse "${release_tag}^{commit}")" ]]; then
  echo "Check out the release tag before preparing its archives" >&2
  exit 1
fi
if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
  echo "Commit tracked source changes before preparing a release" >&2
  exit 1
fi

release_version="${release_tag#v}"
for module_file in MODULE.bazel examples/consuming/MODULE.bazel; do
  if ! grep -Fq "version = \"${release_version}\"" "$module_file"; then
    echo "Update the java_toolchains version in ${module_file} to ${release_version}" >&2
    exit 1
  fi
done

bazelisk build //docs:extensions //docs:repositories >&2
mkdir -p dist
git archive --format=tar.gz \
  --output="dist/java_toolchains-${release_tag}.tar.gz" "$release_tag"
tar -czf "dist/java_toolchains-${release_tag}.docs.tar.gz" \
  -C bazel-bin/docs extensions.binaryproto repositories.binaryproto

cat <<EOF
Non-LTS JDK toolchains for Bazel, built on rules_java.

Install java_toolchains ${release_version} using the source archive attached to
this release. A plain bazel_dep is available after this version is admitted
to the Bazel Central Registry. See README.md for toolchain selection flags
and the supported platform catalog.
EOF
