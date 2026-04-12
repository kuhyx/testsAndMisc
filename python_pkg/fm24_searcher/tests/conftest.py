"""Shared fixtures for FM24 searcher tests."""

from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True, scope="session")
def _offscreen_qt() -> None:
    """Force offscreen Qt platform for headless testing."""
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
