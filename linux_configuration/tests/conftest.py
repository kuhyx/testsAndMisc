"""Pytest bootstrap: make usage_report's ``bin/`` importable for these tests.

The usage-report modules live in a non-package script directory and use
absolute imports (``from _usage_report_parsing import ...``), so the directory
must be on ``sys.path`` before the tests import them.
"""

from __future__ import annotations

from pathlib import Path
import sys

_BIN = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "periodic_background"
    / "system-maintenance"
    / "bin"
)
if str(_BIN) not in sys.path:
    sys.path.insert(0, str(_BIN))
