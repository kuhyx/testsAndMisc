"""Pytest bootstrap: make non-package script dirs importable for these tests.

Several helper modules live in standalone script directories (outside
``python_pkg/``) and are invoked as ``python <file>.py`` rather than imported as
packages. To unit-test them they must be importable by bare module name, so each
directory is placed on ``sys.path`` before the tests import them.
"""

from __future__ import annotations

from pathlib import Path
import sys

# Repo root is two levels up from this file (linux_configuration/tests/conftest.py).
_REPO_ROOT = Path(__file__).resolve().parents[2]

# Each standalone script directory whose Python modules these tests import.
_SCRIPT_DIRS = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "periodic_background"
    / "system-maintenance"
    / "bin",  # usage_report modules
    _REPO_ROOT / "meta" / "scripts",  # validate_evidence, validate_contract
    _REPO_ROOT / "phone_focus_mode" / "lib",  # monitor_report
    _REPO_ROOT / "phone_focus_mode",  # strip_workout_hosts
    _REPO_ROOT
    / "linux_configuration"
    / "scripts"
    / "single_use"
    / "utils",  # fast_count
)

for _script_dir in _SCRIPT_DIRS:
    if str(_script_dir) not in sys.path:
        sys.path.insert(0, str(_script_dir))
