"""Tests for the offline translator module."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator

# Import the module
try:
    from python_pkg.word_frequency import translator
    from python_pkg.word_frequency.translator import (
        TranslationResult,
        download_languages,
        format_translations,
        get_available_packages,
        get_installed_languages,
        main,
        read_file,
        translate_word,
        translate_words,
        translate_words_batch,
    )
except ImportError:
    # Direct execution support
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
    from python_pkg.word_frequency import translator
    from python_pkg.word_frequency.translator import (
        TranslationResult,
        download_languages,
        format_translations,
        get_available_packages,
        get_installed_languages,
        main,
        read_file,
        translate_word,
        translate_words,
        translate_words_batch,
    )


# Helper context manager for mocking argostranslate
class ArgosAvailableMock:
    """Context manager to mock argostranslate being available and control its output.

    Works whether argos is installed or not by patching sys.modules.
    """

    def __init__(
        self, translate_returns: str | list[str] | Exception | None = None
    ) -> None:
        """Initialize with return values for translate()."""
        self.translate_returns = translate_returns
        self.mock_translate_fn = MagicMock()
        self.mock_translate_module = MagicMock()
        self.mock_package_module = MagicMock()
        self.mock_parent = MagicMock()
        self.original_available = translator._argos_available
        self._sys_modules_patcher: MagicMock | None = None
        self._ensure_patcher: MagicMock | None = None
        self._lang_patcher: MagicMock | None = None

    def __enter__(self) -> MagicMock:
        """Set up the mocks."""
        translator._argos_available = True

        # Set up translate return value
        if isinstance(self.translate_returns, Exception) or isinstance(
            self.translate_returns, list
        ):
            self.mock_translate_fn.side_effect = self.translate_returns
        elif self.translate_returns is not None:
            self.mock_translate_fn.return_value = self.translate_returns

        # Wire up the mock modules
        self.mock_translate_module.translate = self.mock_translate_fn
        self.mock_translate_module.get_installed_languages = MagicMock(return_value=[])
        self.mock_package_module.update_package_index = MagicMock()
        self.mock_package_module.get_available_packages = MagicMock(return_value=[])
        self.mock_parent.translate = self.mock_translate_module
        self.mock_parent.package = self.mock_package_module

        # Patch sys.modules to inject our mock (works even if argos not installed)
        self._sys_modules_patcher = patch.dict(
            "sys.modules",
            {
                "argostranslate": self.mock_parent,
                "argostranslate.translate": self.mock_translate_module,
                "argostranslate.package": self.mock_package_module,
            },
        )

        # Patch _ensure_argos_installed and _ensure_language_pair to no-op
        self._ensure_patcher = patch.object(
            translator, "_ensure_argos_installed", lambda: None
        )
        self._lang_patcher = patch.object(
            translator, "_ensure_language_pair", lambda f, t: None
        )

        self._sys_modules_patcher.start()  # type: ignore[union-attr]
        self._ensure_patcher.start()  # type: ignore[union-attr]
        self._lang_patcher.start()  # type: ignore[union-attr]

        return self.mock_translate_fn

    def __exit__(self, *args: object) -> None:
        """Restore original state."""
        if self._lang_patcher:
            self._lang_patcher.stop()
        if self._ensure_patcher:
            self._ensure_patcher.stop()
        if self._sys_modules_patcher:
            self._sys_modules_patcher.stop()
        translator._argos_available = self.original_available


# Fixtures


@pytest.fixture
def mock_argos_unavailable() -> Generator[None, None, None]:
    """Mock argostranslate being unavailable (for legacy tests)."""
    original_value = translator._argos_available
    translator._argos_available = False
    yield
    translator._argos_available = original_value


@pytest.fixture
def temp_words_file(tmp_path: Path) -> Path:
    """Create a temporary file with words."""
    words_file = tmp_path / "words.txt"
    words_file.write_text("hello\nworld\ngoodbye\n", encoding="utf-8")
    return words_file


# TranslationResult tests


class TestTranslationResult:
    """Tests for TranslationResult namedtuple."""

    def test_successful_result(self) -> None:
        """Test creating a successful translation result."""
        result = TranslationResult(
            source_word="hello",
            translated_word="hola",
            source_lang="en",
            target_lang="es",
            success=True,
        )
        assert result.source_word == "hello"
        assert result.translated_word == "hola"
        assert result.source_lang == "en"
        assert result.target_lang == "es"
        assert result.success is True
        assert result.error is None

    def test_failed_result(self) -> None:
        """Test creating a failed translation result."""
        result = TranslationResult(
            source_word="xyz",
            translated_word="",
            source_lang="en",
            target_lang="xx",
            success=False,
            error="Language not supported",
        )
        assert result.success is False
        assert result.error == "Language not supported"

    def test_result_is_tuple(self) -> None:
        """Test that TranslationResult is a namedtuple."""
        result = TranslationResult("a", "b", "en", "es", True)
        assert isinstance(result, tuple)
        assert len(result) == 6


# translate_word tests


class TestTranslateWord:
    """Tests for translate_word function - offline-first behavior."""

    def test_translate_word_argos_unavailable_raises(self) -> None:
        """Test that translation raises ImportError when argos is unavailable."""
        # Mock _ensure_argos_installed to raise ImportError
        with patch.object(
            translator,
            "_ensure_argos_installed",
            side_effect=ImportError("argostranslate not available"),
        ):
            with pytest.raises(ImportError, match="argostranslate not available"):
                translate_word("hello", "en", "es", use_cache=False)

    def test_translate_word_success(self) -> None:
        """Test successful word translation."""
        with ArgosAvailableMock("hola"):
            result = translate_word("hello", "en", "es", use_cache=False)

        assert result.source_word == "hello"
        assert result.translated_word == "hola"
        assert result.success is True

    def test_translate_word_argos_exception_returns_error(self) -> None:
        """Test that argos exception returns failed result with error."""
        # Mock argos being available but translate raising an exception
        with ArgosAvailableMock(RuntimeError("Translation failed")):
            result = translate_word("hello", "en", "es", use_cache=False)

        assert result.success is False
        assert "Translation failed" in str(result.error)


# translate_words tests


class TestTranslateWords:
    """Tests for translate_words function."""

    def test_translate_empty_list(self) -> None:
        """Test translating empty list."""
        # Empty list returns empty result without calling translation
        results = translate_words([], "en", "es")
        assert results == []

    def test_translate_multiple_words(self) -> None:
        """Test translating multiple words."""
        with ArgosAvailableMock(["hola", "mundo"]) as mock:
            mock.side_effect = ["hola", "mundo"]
            results = translate_words(["hello", "world"], "en", "es", use_cache=False)

        assert len(results) == 2
        assert results[0].translated_word == "hola"
        assert results[1].translated_word == "mundo"

    def test_translate_words_argos_unavailable_raises(self) -> None:
        """Test that translating words raises ImportError when argos unavailable."""
        with patch.object(
            translator,
            "_ensure_argos_installed",
            side_effect=ImportError("argostranslate not available"),
        ):
            with pytest.raises(ImportError, match="argostranslate not available"):
                translate_words(["hello", "world"], "en", "es", use_cache=False)


# translate_words_batch tests


class TestTranslateWordsBatch:
    """Tests for translate_words_batch function - offline-first."""

    def test_batch_empty_list(self) -> None:
        """Test batch translation of empty list."""
        # Empty list doesn't require argos
        with patch.object(translator, "_ensure_argos_installed", lambda: None):
            results = translate_words_batch([], "en", "es")
        assert results == []

    def test_batch_small_list(self) -> None:
        """Test batch translation of small list (uses batch mode anyway)."""
        with ArgosAvailableMock("uno\ndos\ntres") as mock:
            results = translate_words_batch(
                ["one", "two", "three"], "en", "es", use_cache=False
            )

        assert len(results) == 3
        # Batch translation
        assert mock.call_count == 1

    def test_batch_large_list_success(self) -> None:
        """Test batch translation of large list."""
        words = ["one", "two", "three", "four", "five"]

        with ArgosAvailableMock("uno\ndos\ntres\ncuatro\ncinco") as mock:
            results = translate_words_batch(words, "en", "es", use_cache=False)

        assert len(results) == 5
        # Batch translation called once
        mock.assert_called_once()
        assert results[0].translated_word == "uno"
        assert results[4].translated_word == "cinco"

    def test_batch_fallback_on_mismatch(self) -> None:
        """Test batch translation falls back to individual when result count mismatches."""
        words = ["one", "two", "three", "four"]
        # First call (batch) returns wrong count, subsequent calls are individual
        with ArgosAvailableMock(["wrong", "uno", "dos", "tres", "cuatro"]) as mock:
            results = translate_words_batch(words, "en", "es", use_cache=False)

        assert len(results) == 4
        # Fallback to individual argos translation
        assert mock.call_count == 5

    def test_batch_fallback_on_exception(self) -> None:
        """Test batch translation raises on exception (no fallback to online)."""
        words = ["one", "two", "three", "four"]

        # Create mock that raises
        mock_translate = MagicMock(side_effect=RuntimeError("Batch failed"))
        mock_translate_module = MagicMock()
        mock_translate_module.translate = mock_translate
        mock_package_module = MagicMock()
        mock_parent = MagicMock()
        mock_parent.translate = mock_translate_module
        mock_parent.package = mock_package_module

        original = translator._argos_available
        translator._argos_available = True

        with (
            patch.dict(
                "sys.modules",
                {
                    "argostranslate": mock_parent,
                    "argostranslate.translate": mock_translate_module,
                    "argostranslate.package": mock_package_module,
                },
            ),
            patch.object(translator, "_ensure_argos_installed", lambda: None),
            patch.object(translator, "_ensure_language_pair", lambda f, t: None),
            pytest.raises(RuntimeError, match="Translation failed"),
        ):
            translate_words_batch(words, "en", "es", use_cache=False)

        translator._argos_available = original

    def test_batch_argos_unavailable_raises(self) -> None:
        """Test that batch translation raises ImportError when argos unavailable."""
        with patch.object(
            translator,
            "_ensure_argos_installed",
            side_effect=ImportError("argostranslate not available"),
        ):
            with pytest.raises(ImportError, match="argostranslate not available"):
                translate_words_batch(["hello", "world"], "en", "es", use_cache=False)


# format_translations tests


class TestFormatTranslations:
    """Tests for format_translations function."""

    def test_format_empty(self) -> None:
        """Test formatting empty results."""
        output = format_translations([])
        assert output == "No translations."

    def test_format_single_translation(self) -> None:
        """Test formatting single translation."""
        results = [
            TranslationResult("hello", "hola", "en", "es", True),
        ]
        output = format_translations(results)

        assert "en -> es" in output
        assert "hello" in output
        assert "hola" in output

    def test_format_multiple_translations(self) -> None:
        """Test formatting multiple translations."""
        results = [
            TranslationResult("hello", "hola", "en", "es", True),
            TranslationResult("world", "mundo", "en", "es", True),
        ]
        output = format_translations(results)

        assert "hello" in output
        assert "hola" in output
        assert "world" in output
        assert "mundo" in output

    def test_format_with_errors(self) -> None:
        """Test formatting with failed translations."""
        results = [
            TranslationResult("hello", "hola", "en", "es", True),
            TranslationResult("xyz", "", "en", "es", False, "Unknown word"),
        ]
        output = format_translations(results, show_errors=True)

        assert "hello" in output
        assert "Error: Unknown word" in output

    def test_format_hide_errors(self) -> None:
        """Test formatting with errors hidden."""
        results = [
            TranslationResult("hello", "hola", "en", "es", True),
            TranslationResult("xyz", "", "en", "es", False, "Unknown word"),
        ]
        output = format_translations(results, show_errors=False)

        assert "hello" in output
        assert "Unknown word" not in output


# get_installed_languages tests


class TestGetInstalledLanguages:
    """Tests for get_installed_languages function."""

    def test_argos_unavailable(self, mock_argos_unavailable: None) -> None:
        """Test when argos is unavailable."""
        result = get_installed_languages()
        assert result == []

    def test_returns_languages(self) -> None:
        """Test returning installed languages."""
        mock_lang1 = MagicMock()
        mock_lang1.code = "en"
        mock_lang1.name = "English"
        mock_lang2 = MagicMock()
        mock_lang2.code = "es"
        mock_lang2.name = "Spanish"

        # We need to mock the translate module's get_installed_languages
        mock_translate_module = MagicMock()
        mock_translate_module.get_installed_languages.return_value = [
            mock_lang1,
            mock_lang2,
        ]
        mock_package_module = MagicMock()
        mock_parent = MagicMock()
        mock_parent.translate = mock_translate_module
        mock_parent.package = mock_package_module

        original = translator._argos_available
        translator._argos_available = True

        with patch.dict(
            "sys.modules",
            {
                "argostranslate": mock_parent,
                "argostranslate.translate": mock_translate_module,
                "argostranslate.package": mock_package_module,
            },
        ):
            result = get_installed_languages()

        translator._argos_available = original

        assert ("en", "English") in result
        assert ("es", "Spanish") in result


# get_available_packages tests


class TestGetAvailablePackages:
    """Tests for get_available_packages function."""

    def test_argos_unavailable(self, mock_argos_unavailable: None) -> None:
        """Test when argos is unavailable."""
        result = get_available_packages()
        assert result == []


# download_languages tests


class TestDownloadLanguages:
    """Tests for download_languages function."""

    def test_argos_unavailable(self, mock_argos_unavailable: None) -> None:
        """Test when argos is unavailable."""
        result = download_languages(["en", "es"])
        assert result == {}


# read_file tests


class TestReadFile:
    """Tests for read_file function."""

    def test_read_file(self, tmp_path: Path) -> None:
        """Test reading a file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello\nworld", encoding="utf-8")

        content = read_file(test_file)

        assert content == "hello\nworld"

    def test_read_file_not_found(self, tmp_path: Path) -> None:
        """Test reading non-existent file."""
        with pytest.raises(FileNotFoundError):
            read_file(tmp_path / "nonexistent.txt")


# main function tests


class TestMain:
    """Tests for main CLI function."""

    def test_argos_unavailable_error(self, mock_argos_unavailable: None) -> None:
        """Test error when argos not installed."""
        result = main(["--text", "hello", "--from", "en", "--to", "es"])
        assert result == 1

    def test_list_languages_empty(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test listing languages when none installed."""
        mock_translate_module = MagicMock()
        mock_translate_module.get_installed_languages.return_value = []
        mock_package_module = MagicMock()
        mock_parent = MagicMock()
        mock_parent.translate = mock_translate_module
        mock_parent.package = mock_package_module

        original = translator._argos_available
        translator._argos_available = True

        with patch.dict(
            "sys.modules",
            {
                "argostranslate": mock_parent,
                "argostranslate.translate": mock_translate_module,
                "argostranslate.package": mock_package_module,
            },
        ):
            result = main(["--list-languages"])

        translator._argos_available = original

        assert result == 0
        captured = capsys.readouterr()
        assert "No languages installed" in captured.out

    def test_list_languages_with_results(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test listing installed languages."""
        mock_lang = MagicMock()
        mock_lang.code = "en"
        mock_lang.name = "English"

        mock_translate_module = MagicMock()
        mock_translate_module.get_installed_languages.return_value = [mock_lang]
        mock_package_module = MagicMock()
        mock_parent = MagicMock()
        mock_parent.translate = mock_translate_module
        mock_parent.package = mock_package_module

        original = translator._argos_available
        translator._argos_available = True

        with patch.dict(
            "sys.modules",
            {
                "argostranslate": mock_parent,
                "argostranslate.translate": mock_translate_module,
                "argostranslate.package": mock_package_module,
            },
        ):
            result = main(["--list-languages"])

        translator._argos_available = original

        assert result == 0
        captured = capsys.readouterr()
        assert "en" in captured.out
        assert "English" in captured.out

    def test_translate_single_text(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test translating single text."""
        with ArgosAvailableMock("hola"):
            result = main(["--text", "hello", "--from", "en", "--to", "es"])

        assert result == 0
        captured = capsys.readouterr()
        assert "hello" in captured.out
        assert "hola" in captured.out

    def test_translate_multiple_words(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test translating multiple words."""
        with ArgosAvailableMock(["hola", "mundo"]):
            result = main(["--words", "hello", "world", "--from", "en", "--to", "es"])

        assert result == 0
        captured = capsys.readouterr()
        assert "hello" in captured.out
        assert "world" in captured.out

    def test_translate_from_file(
        self,
        temp_words_file: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Test translating words from file."""
        with ArgosAvailableMock(["hola", "mundo", "adios"]):
            result = main(
                ["--words-file", str(temp_words_file), "--from", "en", "--to", "es"]
            )

        assert result == 0
        captured = capsys.readouterr()
        assert "hello" in captured.out
        assert "world" in captured.out
        assert "goodbye" in captured.out

    def test_translate_file_not_found(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test error when words file not found."""
        with ArgosAvailableMock():
            result = main(
                ["--words-file", "/nonexistent/file.txt", "--from", "en", "--to", "es"]
            )

        assert result == 1
        captured = capsys.readouterr()
        assert "File not found" in captured.err

    def test_translate_output_to_file(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Test outputting translations to file."""
        output_file = tmp_path / "output.txt"

        with ArgosAvailableMock("hola"):
            result = main(
                [
                    "--text",
                    "hello",
                    "--from",
                    "en",
                    "--to",
                    "es",
                    "--output",
                    str(output_file),
                ]
            )

        assert result == 0
        assert output_file.exists()
        content = output_file.read_text(encoding="utf-8")
        assert "hello" in content
        assert "hola" in content

    def test_no_input_shows_help(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test that no input shows help."""
        with ArgosAvailableMock():
            result = main([])

        assert result == 1

    def test_translation_failure_returns_error(self) -> None:
        """Test that translation failure returns error code when argos unavailable."""
        with patch.object(
            translator,
            "_ensure_argos_installed",
            side_effect=ImportError("argostranslate not available"),
        ):
            result = main(["--text", "hello", "--from", "en", "--to", "es"])
        assert result == 1


# Integration-style tests (still mocked but testing more flow)


class TestIntegration:
    """Integration-style tests for translator."""

    def test_full_translation_flow(self) -> None:
        """Test complete translation flow."""
        with ArgosAvailableMock(["uno", "dos", "tres"]) as mock:
            mock.side_effect = ["uno", "dos", "tres"]
            words = ["one", "two", "three"]
            results = translate_words(words, "en", "es", use_cache=False)

        assert all(r.success for r in results)
        assert [r.translated_word for r in results] == ["uno", "dos", "tres"]

        output = format_translations(results)
        assert "en -> es" in output
        assert "one" in output
        assert "uno" in output

    def test_mixed_success_failure(self) -> None:
        """Test handling when argos raises exception for some translations."""
        # Simulate argos translating first word, then failing, then succeeding
        with ArgosAvailableMock() as mock:
            mock.side_effect = ["hola", RuntimeError("Unknown"), "mundo"]
            results = translate_words(
                ["hello", "xyz", "world"], "en", "es", use_cache=False
            )

        # First and third succeed, second fails
        assert results[0].success is True
        assert results[1].success is False
        assert results[2].success is True

        output = format_translations(results)
        assert "Error" in output
