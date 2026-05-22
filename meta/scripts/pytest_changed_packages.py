#!/usr/bin/env python3
"""Run pytest only for python_pkg subpackages that have changed files.

Used as a pre-commit hook entry point.  Receives staged file paths as
arguments, determines which ``python_pkg/<subpackage>/`` directories are
affected, and runs pytest scoped to just those subpackages in a single
invocation parallelized with pytest-xdist (-n auto).

If a file outside any subpackage is changed (e.g. ``python_pkg/conftest.py``),
all tests are run as a fallback.
"""

from __future__ import annotations

import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys

_MIN_SUBPACKAGE_DEPTH = 2
_TOTAL_MEM = "4G"


_RUN_ALL_TRIGGERS = frozenset({"conftest.py", "__init__.py"})


def _affected_packages(files: list[str]) -> set[str] | None:
    """Return subpackage names touched by *files*, or ``None`` for all."""
    packages: set[str] = set()
    root = Path("python_pkg")
    for path in files:
        parts = PurePosixPath(path).parts
        if len(parts) < _MIN_SUBPACKAGE_DEPTH or parts[0] != "python_pkg":
            continue
        if len(parts) == _MIN_SUBPACKAGE_DEPTH:
            name = parts[1]
            if name in _RUN_ALL_TRIGGERS and (root / name).is_file():
                return None
            continue
        pkg = parts[1]
        if (root / pkg / "tests").is_dir():
            packages.add(pkg)
    return packages


def _build_pytest_command(packages: set[str]) -> list[str]:
    """Build a single pytest invocation covering *packages* in parallel."""
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "--cov-branch",
        "--cov-report=term-missing",
        "--cov-fail-under=100",
        "-q",
        "-n",
        "4",
        # Override addopts from pyproject.toml to drop the global
        # --cov=python_pkg that would widen coverage to the entire tree.
        "-o",
        "addopts=--strict-markers --strict-config -ra",
    ]
    for pkg in sorted(packages):
        cmd.extend(["--cov", f"python_pkg/{pkg}"])
    cmd.extend(f"python_pkg/{pkg}/tests" for pkg in sorted(packages))
    return cmd


def main() -> int:
    """Entry point."""
    files = sys.argv[1:]
    if not files:
        return 0

    packages = _affected_packages(files)

    if packages is None:
        # Root-level python_pkg file changed -> discover every subpackage.
        packages = {
            entry.name
            for entry in Path("python_pkg").iterdir()
            if (entry / "tests").is_dir()
        }

    if not packages:
        return 0

    cmd = _build_pytest_command(packages)
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
