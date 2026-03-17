"""Shared fixtures for translator tests."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path

from python_pkg.word_frequency import translator


@pytest.fixture
def _mock_argos_unavailable() -> Generator[None, None, None]:
    """Mock argostranslate being unavailable (for legacy tests)."""
    with patch.object(translator, "_check_argos", return_value=False):
        yield


@pytest.fixture
def temp_words_file(tmp_path: Path) -> Path:
    """Create a temporary file with words."""
    words_file = tmp_path / "words.txt"
    words_file.write_text("hello\nworld\ngoodbye\n", encoding="utf-8")
    return words_file
