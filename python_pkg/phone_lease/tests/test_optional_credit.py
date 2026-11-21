"""Phone tooling must run when kuhy_credit is not importable.

phone_deploy.sh and the android_ui driver start these CLIs with whatever
``python3`` is first on PATH (often a project venv without kuhy-credit).
The credit is decoration; a missing package must never block a phone lease.
"""

from __future__ import annotations

import subprocess
import sys

from kuhy_credit import credit_line
import pytest

from python_pkg._optional_credit import help_epilog

# Blocks kuhy_credit (sys.modules[name] = None makes import raise
# ImportError), then runs the module as ``python -m <module> --help`` would.
_RUN_WITHOUT_CREDIT = (
    "import runpy, sys; sys.modules['kuhy_credit'] = None; "
    "sys.argv = [sys.argv[1], '--help']; "
    "runpy.run_module(sys.argv[0], run_name='__main__', alter_sys=True)"
)

PHONE_CLIS = ("python_pkg.phone_lease", "python_pkg.android_ui")


@pytest.mark.parametrize("module", PHONE_CLIS)
def test_help_works_without_kuhy_credit(module: str) -> None:
    """``--help`` exits 0 even when kuhy_credit cannot be imported."""
    result = subprocess.run(
        [sys.executable, "-c", _RUN_WITHOUT_CREDIT, module],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "usage" in result.stdout.lower()


def test_help_epilog_none_without_kuhy_credit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """help_epilog() returns None when kuhy_credit cannot be imported."""
    monkeypatch.setitem(sys.modules, "kuhy_credit", None)
    assert help_epilog() is None


def test_help_epilog_is_credit_line() -> None:
    """help_epilog() returns the shared credit line when it is installed."""
    assert help_epilog() == credit_line()
