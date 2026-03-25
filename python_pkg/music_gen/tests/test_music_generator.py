"""Tests for python_pkg.music_gen.music_generator module."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from python_pkg.music_gen.music_generator import (
    check_dependencies,
    interactive_mode,
)

if TYPE_CHECKING:
    import pytest


class TestCheckDependencies:
    """Tests for check_dependencies()."""

    def test_all_present(self) -> None:
        with patch("importlib.util.find_spec", return_value=MagicMock()):
            assert check_dependencies() is True

    def test_torch_missing(self, caplog: pytest.LogCaptureFixture) -> None:
        def mock_find_spec(name: str) -> MagicMock | None:
            if name == "torch":
                return None
            return MagicMock()

        with (
            caplog.at_level(logging.DEBUG),
            patch("importlib.util.find_spec", side_effect=mock_find_spec),
        ):
            assert check_dependencies() is False

        assert "torch" in caplog.text

    def test_transformers_missing(self, caplog: pytest.LogCaptureFixture) -> None:
        def mock_find_spec(name: str) -> MagicMock | None:
            if name == "transformers":
                return None
            return MagicMock()

        with (
            caplog.at_level(logging.DEBUG),
            patch("importlib.util.find_spec", side_effect=mock_find_spec),
        ):
            assert check_dependencies() is False

        assert "transformers" in caplog.text

    def test_scipy_missing(self, caplog: pytest.LogCaptureFixture) -> None:
        def mock_find_spec(name: str) -> MagicMock | None:
            if name == "scipy":
                return None
            return MagicMock()

        with (
            caplog.at_level(logging.DEBUG),
            patch("importlib.util.find_spec", side_effect=mock_find_spec),
        ):
            assert check_dependencies() is False

        assert "scipy" in caplog.text

    def test_bark_missing_with_include_bark(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        def mock_find_spec(name: str) -> MagicMock | None:
            if name == "bark":
                return None
            return MagicMock()

        with (
            caplog.at_level(logging.DEBUG),
            patch("importlib.util.find_spec", side_effect=mock_find_spec),
        ):
            assert check_dependencies(include_bark=True) is False

        assert "bark" in caplog.text.lower()

    def test_bark_not_checked_without_flag(self) -> None:
        with patch("importlib.util.find_spec", return_value=MagicMock()):
            assert check_dependencies(include_bark=False) is True

    def test_all_present_with_bark(self) -> None:
        with patch("importlib.util.find_spec", return_value=MagicMock()):
            assert check_dependencies(include_bark=True) is True


class TestInteractiveMode:
    """Tests for interactive_mode()."""

    def test_quit_command(self, caplog: pytest.LogCaptureFixture) -> None:
        with (
            caplog.at_level(logging.DEBUG),
            patch("builtins.input", return_value=":q"),
        ):
            interactive_mode(MagicMock(), MagicMock())

        assert "Exiting" in caplog.text

    def test_quit_word(self, caplog: pytest.LogCaptureFixture) -> None:
        with (
            caplog.at_level(logging.DEBUG),
            patch("builtins.input", return_value="quit"),
        ):
            interactive_mode(MagicMock(), MagicMock())

        assert "Exiting" in caplog.text

    def test_exit_word(self) -> None:
        with patch("builtins.input", return_value="exit"):
            interactive_mode(MagicMock(), MagicMock())

    def test_help_command(self, caplog: pytest.LogCaptureFixture) -> None:
        with (
            caplog.at_level(logging.DEBUG),
            patch("builtins.input", side_effect=[":h", ":q"]),
        ):
            interactive_mode(MagicMock(), MagicMock())

        assert "Example prompts" in caplog.text

    def test_help_word(self, caplog: pytest.LogCaptureFixture) -> None:
        with (
            caplog.at_level(logging.DEBUG),
            patch("builtins.input", side_effect=["help", ":q"]),
        ):
            interactive_mode(MagicMock(), MagicMock())

        assert "Example prompts" in caplog.text

    def test_set_duration(self, caplog: pytest.LogCaptureFixture) -> None:
        with (
            caplog.at_level(logging.DEBUG),
            patch("builtins.input", side_effect=[":d 15", ":q"]),
        ):
            interactive_mode(MagicMock(), MagicMock())

        assert "Duration set to 15s" in caplog.text

    def test_set_duration_clamped(self, caplog: pytest.LogCaptureFixture) -> None:
        with (
            caplog.at_level(logging.DEBUG),
            patch("builtins.input", side_effect=[":d 100", ":q"]),
        ):
            interactive_mode(MagicMock(), MagicMock())

        assert "Duration set to 30s" in caplog.text

    def test_set_duration_invalid(self, caplog: pytest.LogCaptureFixture) -> None:
        with (
            caplog.at_level(logging.DEBUG),
            patch("builtins.input", side_effect=[":d abc", ":q"]),
        ):
            interactive_mode(MagicMock(), MagicMock())

        assert "Invalid duration" in caplog.text

    def test_empty_prompt(self) -> None:
        with patch("builtins.input", side_effect=["", ":q"]):
            interactive_mode(MagicMock(), MagicMock())

    def test_number_prompt_valid(self) -> None:
        with (
            patch("builtins.input", side_effect=["1", ":q"]),
            patch(
                "python_pkg.music_gen.music_generator.generate_music",
            ) as mock_gen,
        ):
            interactive_mode(MagicMock(), MagicMock())

        mock_gen.assert_called_once()

    def test_number_prompt_invalid(self, caplog: pytest.LogCaptureFixture) -> None:
        with (
            caplog.at_level(logging.DEBUG),
            patch("builtins.input", side_effect=["99", ":q"]),
        ):
            interactive_mode(MagicMock(), MagicMock())

        assert "Invalid number" in caplog.text

    def test_normal_prompt(self) -> None:
        with (
            patch("builtins.input", side_effect=["jazz music", ":q"]),
            patch(
                "python_pkg.music_gen.music_generator.generate_music",
            ) as mock_gen,
        ):
            interactive_mode(MagicMock(), MagicMock())

        mock_gen.assert_called_once()

    def test_generation_error(self, caplog: pytest.LogCaptureFixture) -> None:
        with (
            caplog.at_level(logging.DEBUG),
            patch("builtins.input", side_effect=["jazz music", ":q"]),
            patch(
                "python_pkg.music_gen.music_generator.generate_music",
                side_effect=RuntimeError("CUDA OOM"),
            ),
        ):
            interactive_mode(MagicMock(), MagicMock())

        assert "Error generating music" in caplog.text

    def test_eof_error(self, caplog: pytest.LogCaptureFixture) -> None:
        with (
            caplog.at_level(logging.DEBUG),
            patch("builtins.input", side_effect=EOFError),
        ):
            interactive_mode(MagicMock(), MagicMock())

        assert "Exiting" in caplog.text

    def test_keyboard_interrupt(self, caplog: pytest.LogCaptureFixture) -> None:
        with (
            caplog.at_level(logging.DEBUG),
            patch("builtins.input", side_effect=KeyboardInterrupt),
        ):
            interactive_mode(MagicMock(), MagicMock())

        assert "Exiting" in caplog.text

    def test_quit_long(self, caplog: pytest.LogCaptureFixture) -> None:
        with (
            caplog.at_level(logging.DEBUG),
            patch("builtins.input", return_value=":quit"),
        ):
            interactive_mode(MagicMock(), MagicMock())

        assert "Exiting" in caplog.text

    def test_help_long(self, caplog: pytest.LogCaptureFixture) -> None:
        with (
            caplog.at_level(logging.DEBUG),
            patch("builtins.input", side_effect=[":help", ":q"]),
        ):
            interactive_mode(MagicMock(), MagicMock())

        assert "Example prompts" in caplog.text

    def test_duration_clamp_minimum(self, caplog: pytest.LogCaptureFixture) -> None:
        with (
            caplog.at_level(logging.DEBUG),
            patch("builtins.input", side_effect=[":d 0", ":q"]),
        ):
            interactive_mode(MagicMock(), MagicMock())

        assert "Duration set to 1s" in caplog.text

    def test_generation_value_error(self, caplog: pytest.LogCaptureFixture) -> None:
        with (
            caplog.at_level(logging.DEBUG),
            patch("builtins.input", side_effect=["jazz", ":q"]),
            patch(
                "python_pkg.music_gen.music_generator.generate_music",
                side_effect=ValueError("bad value"),
            ),
        ):
            interactive_mode(MagicMock(), MagicMock())

        assert "Error generating music" in caplog.text

    def test_generation_os_error(self, caplog: pytest.LogCaptureFixture) -> None:
        with (
            caplog.at_level(logging.DEBUG),
            patch("builtins.input", side_effect=["jazz", ":q"]),
            patch(
                "python_pkg.music_gen.music_generator.generate_music",
                side_effect=OSError("disk full"),
            ),
        ):
            interactive_mode(MagicMock(), MagicMock())

        assert "Error generating music" in caplog.text
