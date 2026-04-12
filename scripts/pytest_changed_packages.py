#!/usr/bin/env python3
"""Run pytest only for python_pkg subpackages that have changed files.

Used as a pre-commit hook entry point.  Receives staged file paths as
arguments, determines which ``python_pkg/<subpackage>/`` directories are
affected, and runs pytest scoped to just those subpackages.

If a file outside any subpackage is changed (e.g. ``python_pkg/conftest.py``),
all tests are run as a fallback.
"""

from __future__ import annotations

import gc
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tempfile

_MIN_SUBPACKAGE_DEPTH = 2
_PER_PACKAGE_MEM = "2G"


def _affected_packages(files: list[str]) -> set[str] | None:
    """Return subpackage names touched by *files*, or ``None`` for all.

    Returns ``None`` when a root-level ``python_pkg/`` file is modified,
    meaning every test should run.
    """
    packages: set[str] = set()
    for path in files:
        parts = PurePosixPath(path).parts
        if len(parts) < _MIN_SUBPACKAGE_DEPTH or parts[0] != "python_pkg":
            continue
        if len(parts) == _MIN_SUBPACKAGE_DEPTH:
            # Root-level file like python_pkg/conftest.py - run everything.
            return None
        packages.add(parts[1])
    return packages


def _build_pytest_command(packages: set[str] | None) -> list[str]:
    """Build the pytest invocation for the given *packages*."""
    base = [
        sys.executable,
        "-m",
        "pytest",
        "--cov-branch",
        "--cov-report=term-missing",
        "--cov-fail-under=100",
        "-q",
    ]
    if packages is None or not packages:
        # Fallback: run everything.
        return [*base, "--cov=python_pkg"]

    # Override addopts from pyproject.toml to remove the global --cov=python_pkg
    # that would widen coverage measurement to the entire tree.
    cmd = [
        *base,
        "-o",
        "addopts=-v --strict-markers --strict-config -ra",
    ]
    for pkg in sorted(packages):
        cmd.extend(["--cov", f"python_pkg/{pkg}"])
    for pkg in sorted(packages):
        test_dir = f"python_pkg/{pkg}/tests"
        cmd.append(test_dir)
    return cmd


def main() -> int:
    """Entry point."""
    files = sys.argv[1:]
    if not files:
        return 0

    packages = _affected_packages(files)

    # When many packages are affected, run each one in a separate subprocess
    # to avoid accumulating memory across all test suites (OOM prevention).
    if packages is None:
        # Discover all subpackages that have a tests/ directory.
        packages = {
            entry.name
            for entry in Path("python_pkg").iterdir()
            if (entry / "tests").is_dir()
        }

    if not packages:
        return 0

    # Run each package in its own subprocess so memory is freed between runs.
    # Wrap each in a nested cgroup with MemorySwapMax=0 so it gets killed
    # instantly at the limit instead of thrashing swap/zram.
    use_cgroup = shutil.which("systemd-run") is not None
    for pkg in sorted(packages):
        # Each package gets its own isolated coverage data file so parallel
        # cgroup subprocesses never stomp on each other's SQLite DB.
        with tempfile.NamedTemporaryFile(
            prefix=f".coverage_{pkg}_", dir=".", delete=False
        ) as tmp:
            cov_file = tmp.name
        try:
            cmd = _build_pytest_command({pkg})
            env = {**os.environ, "COVERAGE_FILE": cov_file}
            if use_cgroup:
                cmd = [
                    "systemd-run",
                    "--user",
                    "--scope",
                    "-p",
                    f"MemoryMax={_PER_PACKAGE_MEM}",
                    "-p",
                    "MemorySwapMax=0",
                    *cmd,
                ]
            result = subprocess.run(cmd, check=False, env=env)
        finally:
            Path(cov_file).unlink(missing_ok=True)
        gc.collect()
        if result.returncode != 0:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
