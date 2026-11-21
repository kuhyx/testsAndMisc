"""The kuhy credit for CLIs that phone tooling starts under any ``python3``.

phone_deploy.sh and the android_ui driver run with whatever interpreter is
first on PATH, often a project venv without kuhy-credit. The credit is
decoration, so a missing package yields no epilog instead of a crash.
"""

from __future__ import annotations

import importlib


def help_epilog() -> str | None:
    """Return the shared credit line, or None when kuhy_credit is missing."""
    try:
        credit = importlib.import_module("kuhy_credit")
    except ImportError:
        return None
    line: str = credit.credit_line()
    return line
