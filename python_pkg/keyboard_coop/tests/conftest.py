"""Shared fixtures for keyboard_coop tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def mock_pygame() -> MagicMock:
    """Mock pygame to prevent display initialization."""
    with patch.dict("sys.modules", {"pygame": MagicMock()}):
        yield
