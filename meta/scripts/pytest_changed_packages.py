#!/usr/bin/env python3
"""Run pytest for all python_pkg subpackages whenever any Python file changes.

Used as a pre-commit hook entry point. Receives staged file paths as arguments.
If any Python file changed, discovers every subpackage under ``python_pkg/``
that has a ``tests/`` directory and runs them all in a single parallelised
invocation with whole-repo coverage measured against ``python_pkg``.

Running all packages together (rather than just the touched ones) ensures that
100% branch coverage is maintained across the entire codebase on every commit,
not just the files that happened to change.

Standalone script suites outside ``python_pkg/`` (currently
``linux_configuration/tests``) are also run so their behaviour is gated, but
they are not coverage-measured (coverage stays scoped to ``python_pkg``).
"""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys

_TOTAL_MEM = "4G"

# Standalone script test suites outside python_pkg/ that should be gated but
# not coverage-measured. Skipped silently if the directory does not exist.
_EXTRA_TEST_DIRS = ("linux_configuration/tests",)


def main() -> int:
    """Entry point."""
    if not sys.argv[1:]:
        return 0

    packages = sorted(
        entry.name
        for entry in Path("python_pkg").iterdir()
        if (entry / "tests").is_dir()
    )
    if not packages:
        return 0

    test_dirs = [f"python_pkg/{pkg}/tests" for pkg in packages]
    test_dirs += [d for d in _EXTRA_TEST_DIRS if Path(d).is_dir()]

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "--cov",
        "python_pkg",
        "--cov-branch",
        "--cov-report=term-missing",
        "--cov-fail-under=100",
        "-q",
        "-n",
        "4",
        # Override addopts from pyproject.toml to avoid double --cov flags.
        "-o",
        "addopts=--strict-markers --strict-config -ra",
        *test_dirs,
    ]

    if shutil.which("systemd-run") is not None:
        cmd = [
            "systemd-run",
            "--user",
            "--scope",
            "--quiet",
            "--collect",
            "-p",
            f"MemoryMax={_TOTAL_MEM}",
            "-p",
            "MemorySwapMax=0",
            *cmd,
        ]
    return subprocess.run(cmd, check=False, env=os.environ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
