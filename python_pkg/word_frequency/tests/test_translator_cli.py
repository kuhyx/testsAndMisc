"""Tests for word_frequency._translator_cli module."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

import python_pkg.word_frequency._translator_cli as _cli
from python_pkg.word_frequency._translator_cli import (
    _collect_words,
    _handle_download,
    _handle_list_available,
    _handle_list_languages,
    _handle_translation,
    main,
)
from python_pkg.word_frequency._translator_helpers import TranslationResult


class TestHandleListLanguages:
    """Tests for _handle_list_languages."""

    def test_no_languages(self, capsys: pytest.CaptureFixture[str]) -> None:
        with patch.object(_cli._trans, "get_installed_languages", return_value=[]):
            result = _handle_list_languages()
        assert result == 0
        captured = capsys.readouterr()
        assert "No languages installed" in captured.out

    def test_with_languages(self, capsys: pytest.CaptureFixture[str]) -> None:
        with patch.object(
            _cli._trans,
            "get_installed_languages",
            return_value=[("en", "English"), ("es", "Spanish")],
        ):
            result = _handle_list_languages()
        assert result == 0
        captured = capsys.readouterr()
        assert "en" in captured.out
        assert "Spanish" in captured.out


class TestHandleListAvailable:
    """Tests for _handle_list_available."""

    def test_no_packages(self, capsys: pytest.CaptureFixture[str]) -> None:
        with patch.object(_cli._trans, "get_available_packages", return_value=[]):
            result = _handle_list_available()
        assert result == 0
        captured = capsys.readouterr()
        assert "No packages available" in captured.out

    def test_with_packages(self, capsys: pytest.CaptureFixture[str]) -> None:
        with patch.object(
            _cli._trans,
            "get_available_packages",
            return_value=[("en", "English", "es", "Spanish")],
        ):
            result = _handle_list_available()
        assert result == 0
        captured = capsys.readouterr()
        assert "en" in captured.out
        assert "Spanish" in captured.out


class TestHandleDownload:
    """Tests for _handle_download."""

    def test_success(self, capsys: pytest.CaptureFixture[str]) -> None:
        with patch.object(
            _cli._trans,
            "download_languages",
            return_value={"en->es": True, "es->en": True},
        ):
            result = _handle_download(["en", "es"])
        assert result == 0
        captured = capsys.readouterr()
        assert "2/2" in captured.out

    def test_all_fail(self, capsys: pytest.CaptureFixture[str]) -> None:
        with patch.object(
            _cli._trans,
            "download_languages",
            return_value={"en->es": False},
        ):
            result = _handle_download(["en", "es"])
        assert result == 1


class TestCollectWords:
    """Tests for _collect_words."""

    def test_from_text(self) -> None:
        args = MagicMock()
        args.text = "hello"
        args.words = None
        args.words_file = None
        result = _collect_words(args)
        assert result == ["hello"]

    def test_from_words(self) -> None:
        args = MagicMock()
        args.text = None
        args.words = ["hello", "world"]
        args.words_file = None
        result = _collect_words(args)
        assert result == ["hello", "world"]

    def test_from_file(self, tmp_path: Path) -> None:
        f = tmp_path / "words.txt"
        f.write_text("hello\nworld\n", encoding="utf-8")
        args = MagicMock()
        args.text = None
        args.words = None
        args.words_file = str(f)
        with patch.object(_cli._trans, "read_file", return_value="hello\nworld\n"):
            result = _collect_words(args)
        assert result == ["hello", "world"]

    def test_file_not_found(self, capsys: pytest.CaptureFixture[str]) -> None:
        args = MagicMock()
        args.text = None
        args.words = None
        args.words_file = "/nonexistent"
        with patch.object(
            _cli._trans, "read_file", side_effect=FileNotFoundError("not found")
        ):
            result = _collect_words(args)
        assert result is None
        captured = capsys.readouterr()
        assert "File not found" in captured.err

    def test_no_input(self) -> None:
        args = MagicMock()
        args.text = None
        args.words = None
        args.words_file = None
        result = _collect_words(args)
        assert result == []


class TestHandleTranslation:
    """Tests for _handle_translation."""

    def test_success(self, capsys: pytest.CaptureFixture[str]) -> None:
        args = MagicMock()
        args.words = ["hello"]
        args.from_lang = "en"
        args.to_lang = "es"
        args.output = None
        with (
            patch.object(
                _cli._trans,
                "translate_words_batch",
                return_value=[
                    TranslationResult("hello", "hola", "en", "es", True),
                ],
            ),
            patch.object(
                _cli._trans,
                "format_translations",
                return_value="hello -> hola",
            ),
        ):
            result = _handle_translation(args)
        assert result == 0

    def test_import_error(self) -> None:
        args = MagicMock()
        args.words = ["hello"]
        args.from_lang = "en"
        args.to_lang = "es"
        with patch.object(
            _cli._trans,
            "translate_words_batch",
            side_effect=ImportError("no module"),
        ):
            result = _handle_translation(args)
        assert result == 1

    def test_output_to_file(self, tmp_path: Path) -> None:
        out = tmp_path / "out.txt"
        args = MagicMock()
        args.words = ["hello"]
        args.from_lang = "en"
        args.to_lang = "es"
        args.output = str(out)
        with (
            patch.object(
                _cli._trans,
                "translate_words_batch",
                return_value=[
                    TranslationResult("hello", "hola", "en", "es", True),
                ],
            ),
            patch.object(
                _cli._trans,
                "format_translations",
                return_value="hello -> hola",
            ),
        ):
            result = _handle_translation(args)
        assert result == 0
        assert out.exists()

    def test_partial_failure(self, capsys: pytest.CaptureFixture[str]) -> None:
        args = MagicMock()
        args.words = ["hello", "xyz"]
        args.from_lang = "en"
        args.to_lang = "es"
        args.output = None
        with (
            patch.object(
                _cli._trans,
                "translate_words_batch",
                return_value=[
                    TranslationResult("hello", "hola", "en", "es", True),
                    TranslationResult("xyz", "", "en", "es", False, "error"),
                ],
            ),
            patch.object(
                _cli._trans,
                "format_translations",
                return_value="output",
            ),
        ):
            result = _handle_translation(args)
        assert result == 1


class TestMain:
    """Tests for main entry point."""

    def test_argos_not_available(self, capsys: pytest.CaptureFixture[str]) -> None:
        with patch.object(_cli._trans, "_check_argos", return_value=False):
            result = main(["--text", "hello", "--from", "en", "--to", "es"])
        assert result == 1
        captured = capsys.readouterr()
        assert "argostranslate is not installed" in captured.err

    def test_list_languages(self) -> None:
        with (
            patch.object(_cli._trans, "_check_argos", return_value=True),
            patch.object(
                _cli._trans,
                "get_installed_languages",
                return_value=[("en", "English")],
            ),
        ):
            result = main(["--list-languages"])
        assert result == 0

    def test_list_available(self) -> None:
        with (
            patch.object(_cli._trans, "_check_argos", return_value=True),
            patch.object(_cli._trans, "get_available_packages", return_value=[]),
        ):
            result = main(["--list-available"])
        assert result == 0

    def test_download(self, capsys: pytest.CaptureFixture[str]) -> None:
        with (
            patch.object(_cli._trans, "_check_argos", return_value=True),
            patch.object(
                _cli._trans,
                "download_languages",
                return_value={"en->es": True},
            ),
        ):
            result = main(["--download", "en", "es"])
        assert result == 0

    def test_no_input_shows_help(self) -> None:
        with patch.object(_cli._trans, "_check_argos", return_value=True):
            result = main([])
        assert result == 1

    def test_collect_words_returns_none(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        with (
            patch.object(_cli._trans, "_check_argos", return_value=True),
            patch.object(
                _cli._trans,
                "read_file",
                side_effect=FileNotFoundError("nope"),
            ),
        ):
            result = main(
                ["--words-file", "/nonexistent", "--from", "en", "--to", "es"]
            )
        assert result == 1
