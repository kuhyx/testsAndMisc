"""Every argparse/typer CLI in python_pkg ends its --help with the kuhy credit.

Each module runs as ``python -m <module> --help`` in a subprocess, the same
way kuhy and the systemd units start it, so the check covers the real entry
point rather than an internal parser builder.
"""

from __future__ import annotations

import subprocess
import sys

from kuhy_credit import credit_line
import pytest

# Entry points deliberately left without a credit, and why, live in
# docs/superpowers/evidence/kuhy-credit-cli-help-2026-11-21.json.
CREDITED_CLIS = (
    "python_pkg.android_ui",
    "python_pkg.android_ui.workout_firebase_flow",
    "python_pkg.app_icons",
    "python_pkg.archwiki_rag",
    "python_pkg.artgate.cli",
    "python_pkg.code_tutor.cli",
    "python_pkg.js_anki",
    "python_pkg.morning_routine._orchestrator",
    "python_pkg.phone_lease",
    "python_pkg.random_jpg.generate_jpeg",
    "python_pkg.sql_drills",
    "python_pkg.vscode_optimizer",
)


@pytest.mark.parametrize("module", CREDITED_CLIS)
def test_help_ends_with_credit(module: str) -> None:
    """``--help`` exits 0 and prints the shared credit line."""
    result = subprocess.run(
        [sys.executable, "-m", module, "--help"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert credit_line() in result.stdout
