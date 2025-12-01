"""Tests for bot version management."""

from pathlib import Path
from typing import BinaryIO, TextIO
from unittest.mock import patch

import pytest

from python_pkg.lichess_bot.utils import _version_file_path, get_and_increment_version


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
    with version_file.open() as f:
        assert f.read().strip() == "2"


def test_version_file_path_uses_env_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test _version_file_path uses environment variable when set."""
    custom_path = str(tmp_path / "custom_version.txt")
    monkeypatch.setenv("LICHESS_BOT_VERSION_FILE", custom_path)

    result = _version_file_path()
    assert result == custom_path


def test_version_file_path_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test _version_file_path returns default when no env var."""
    monkeypatch.delenv("LICHESS_BOT_VERSION_FILE", raising=False)

    result = _version_file_path()
    assert ".bot_version" in result


def test_get_version_handles_missing_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test get_and_increment_version handles missing file gracefully."""
    version_file = tmp_path / "nonexistent" / "version.txt"
    monkeypatch.setenv("LICHESS_BOT_VERSION_FILE", str(version_file))

    # The directory doesn't exist, but it should handle gracefully
    # First call should fail to read, start from 0, and return 1
    v1 = get_and_increment_version()
    assert v1 == 1


def test_get_version_handles_invalid_content(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test get_and_increment_version handles invalid file content."""
    version_file = tmp_path / "version.txt"
    version_file.write_text("not_a_number")
    monkeypatch.setenv("LICHESS_BOT_VERSION_FILE", str(version_file))

    # Should handle ValueError and treat as version 0
    v1 = get_and_increment_version()
    assert v1 == 1


def test_get_version_handles_empty_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test get_and_increment_version handles empty file."""
    version_file = tmp_path / "version.txt"
    version_file.write_text("")
    monkeypatch.setenv("LICHESS_BOT_VERSION_FILE", str(version_file))

    # Empty file should be treated as version 0
    v1 = get_and_increment_version()
    assert v1 == 1


def test_get_version_handles_write_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test get_and_increment_version handles write failures."""
    version_file = tmp_path / "version.txt"
    monkeypatch.setenv("LICHESS_BOT_VERSION_FILE", str(version_file))

    # Make the parent directory read-only after first call
    v1 = get_and_increment_version()
    assert v1 == 1

    # Mock to simulate write failure
    original_open = Path.open
    write_error_msg = "Simulated write failure"

    def failing_open(
        self: Path, mode: str = "r", *args: object, **kwargs: object
    ) -> TextIO | BinaryIO:
        if "w" in mode and str(self).endswith((".tmp", "version.txt")):
            raise OSError(write_error_msg)
        return original_open(  # type: ignore[call-overload,return-value]
            self, mode, *args, **kwargs
        )

    with patch.object(Path, "open", failing_open):
        # Should still return incremented version even if write fails
        v2 = get_and_increment_version()
        assert v2 == 2


def test_get_version_fallback_direct_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test fallback direct write when replace fails."""
    version_file = tmp_path / "version.txt"
    monkeypatch.setenv("LICHESS_BOT_VERSION_FILE", str(version_file))

    # Create initial version
    v1 = get_and_increment_version()
    assert v1 == 1

    # Mock to make .replace() fail but direct write succeed
    original_replace = Path.replace
    replace_error_msg = "Simulated replace failure"

    def failing_replace(self: Path, target: Path) -> Path:
        if str(self).endswith(".tmp"):
            raise OSError(replace_error_msg)
        return original_replace(self, target)

    with patch.object(Path, "replace", failing_replace):
        v2 = get_and_increment_version()
        assert v2 == 2

    # Version should still be written via fallback
    with version_file.open() as f:
        content = f.read().strip()
        assert content == "2"
