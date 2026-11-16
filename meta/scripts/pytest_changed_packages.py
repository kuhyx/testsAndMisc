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

from importlib import metadata
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

# Memory ceiling for the whole suite. Measured peak RSS for all python_pkg
# tests plus linux_configuration/tests (1117 tests, branch coverage on) is
# ~0.23 GiB, so 2G leaves roughly 8x headroom. It was 4G, which is not free:
# a 4G request cannot be satisfied inside a smaller outer scope, so wrapping
# a commit in a tighter budget got the suite OOM-killed from the inside rather
# than merely slowed. Keep this at or below any outer cap a caller may impose.
_TOTAL_MEM = "2G"

# Standalone script test suites outside python_pkg/ that should be gated but
# not coverage-measured. Skipped silently if the directory does not exist.
_EXTRA_TEST_DIRS = ("linux_configuration/tests",)

# The suite's own dependency list. A pin added here (fastmcp, 2026-11) used to
# reach every checkout whose interpreter never installed it as a collection
# ImportError; the preflight below installs it instead.
_TEST_REQUIREMENTS = Path("meta/requirements-test.txt")
# pip's comment rule: "#" at line start or after whitespace. A bare "#" is a
# URL fragment (``#subdirectory=sql_drills``) and must survive.
_COMMENT = re.compile(r"(^|\s)#.*$")
_DIST_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*")


def _missing_requirements() -> list[str]:
    """Return the ``name==version`` pins whose distribution is not installed."""
    if not _TEST_REQUIREMENTS.is_file():
        return []
    missing = []
    for raw in _TEST_REQUIREMENTS.read_text(encoding="utf-8").splitlines():
        pin = _COMMENT.sub("", raw).strip()
        name = _DIST_NAME.match(pin)
        if name is None:  # blank, or a "-r"/"-c" option line
            continue
        try:
            metadata.distribution(name.group(0))
        except metadata.PackageNotFoundError:
            missing.append(pin)
    return missing


def _install_missing_requirements() -> int:
    """Install absent test pins into this interpreter; 0 when nothing is missing.

    Only ABSENT packages are installed: a present one at another version is
    left alone, so the hook never churns a working environment. Outside a venv
    the system interpreter is externally managed, so it goes to the user site.
    """
    missing = _missing_requirements()
    if not missing:
        return 0
    sys.stdout.write(f"Installing missing test requirements: {' '.join(missing)}\n")
    sys.stdout.flush()
    cmd = [sys.executable, "-m", "pip", "install", "--quiet"]
    if sys.prefix == sys.base_prefix:
        cmd += ["--user", "--break-system-packages"]
    return subprocess.run([*cmd, *missing], check=False).returncode


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

    installed = _install_missing_requirements()
    if installed != 0:
        sys.stderr.write("Installing the missing test requirements failed.\n")
        return installed

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
        # No -n/xdist: pytest-cov's worker coverage combine has shown a
        # reproducible (not flaky -- failed identically twice in a row) gap
        # under -n 4 on the GitHub Actions runner that never occurs running
        # serially, including run repeatedly with the same -n 4 locally.
        # Serial is slightly slower but has never produced a false coverage
        # failure, which matters more for a 100%-coverage gate.
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
