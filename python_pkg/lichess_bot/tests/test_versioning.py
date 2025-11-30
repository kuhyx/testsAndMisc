"""Tests for bot version management."""

from pathlib import Path

import pytest

from python_pkg.lichess_bot.utils import get_and_increment_version


def test_version_file_increments_and_persists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that version increments and persists to file."""
    version_file = tmp_path / "version.txt"
    monkeypatch.setenv("LICHESS_BOT_VERSION_FILE", str(version_file))

    v1 = get_and_increment_version()
    v2 = get_and_increment_version()

    assert v1 == 1
    assert v2 == 2

    # Ensure it persisted
    with open(version_file) as f:
        assert f.read().strip() == "2"
