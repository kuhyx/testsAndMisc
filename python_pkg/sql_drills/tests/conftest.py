"""Keep the optional focus tracker out of every test unless a test fakes it."""

from __future__ import annotations

import sys
from typing import Any, cast

import pytest


@pytest.fixture(autouse=True)
def _no_real_focus_tracker(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make ``import focus_project`` fail, so no test writes live activity."""
    monkeypatch.setitem(sys.modules, "focus_project", cast("Any", None))
