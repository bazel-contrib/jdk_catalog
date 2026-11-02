#!/usr/bin/env python3
"""Check API snapshots without shell path conversion or line-ending differences."""

import difflib
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    root = Path(__file__).resolve().parents[1]
    bazelisk = shutil.which("bazelisk")
    if bazelisk is None:
        raise SystemExit("Install Bazelisk before checking API documentation")
    subprocess.run(
        [
            bazelisk,
            "build",
            "//docs:extensions.textproto",
            "//docs:repositories.textproto",
        ],
        cwd=root,
        check=True,
    )
    bazel_bin = Path(
        subprocess.check_output(
            [bazelisk, "info", "bazel-bin"], cwd=root, text=True
        ).strip()
    )
    matches = True
    for name in ["extensions", "repositories"]:
        snapshot = root / "docs" / f"{name}.textproto"
        generated = bazel_bin / "docs" / snapshot.name
        # read_text() normalizes CRLF checkouts to LF on every platform.
        expected = snapshot.read_text(encoding="utf-8")
        actual = generated.read_text(encoding="utf-8")
        if expected != actual:
            matches = False
            sys.stderr.writelines(
                difflib.unified_diff(
                    expected.splitlines(keepends=True),
                    actual.splitlines(keepends=True),
                    fromfile=str(snapshot),
                    tofile=str(generated),
                )
            )
    return 0 if matches else 1


if __name__ == "__main__":
    sys.exit(main())
