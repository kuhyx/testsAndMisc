"""Tests for translator module - part 1 (results, translation, batch, formatting)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from python_pkg.word_frequency import translator
from python_pkg.word_frequency._translator_helpers import (
    TranslationResult,
    format_translations,
)
from python_pkg.word_frequency.tests._translator_helpers import ArgosAvailableMock
from python_pkg.word_frequency.translator import (
    translate_word,
    translate_words,
    translate_words_batch,
)

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
        result = TranslationResult("a", "b", "en", "es", success=True)
        assert isinstance(result, tuple)
        assert len(result) == 6


# translate_word tests


class TestTranslateWord:
    """Tests for translate_word function - offline-first behavior."""

    def test_translate_word_argos_unavailable_raises(self) -> None:
        """Test that translation raises ImportError when argos is unavailable."""
        # Mock _ensure_argos_installed to raise ImportError
        with (
            patch.object(
                translator,
                "_ensure_argos_installed",
                side_effect=ImportError("argostranslate not available"),
            ),
            pytest.raises(ImportError, match="argostranslate not available"),
        ):
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
        with (
            patch.object(
                translator,
                "_ensure_argos_installed",
                side_effect=ImportError("argostranslate not available"),
            ),
            pytest.raises(ImportError, match="argostranslate not available"),
        ):
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
        """Test batch falls back to individual on result count mismatch."""
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

        with (
            patch.object(translator, "check_argos", return_value=True),
            patch.object(translator, "argostranslate", mock_parent, create=True),
            patch.dict(
                "sys.modules",
                {
                    "argostranslate": mock_parent,
                    "argostranslate.translate": mock_translate_module,
                    "argostranslate.package": mock_package_module,
                },
            ),
            patch.object(translator, "_ensure_argos_installed", lambda: None),
            patch.object(translator, "_ensure_language_pair", lambda _f, _t: None),
            pytest.raises(RuntimeError, match="Translation failed"),
        ):
            translate_words_batch(words, "en", "es", use_cache=False)

    def test_batch_argos_unavailable_raises(self) -> None:
        """Test that batch translation raises ImportError when argos unavailable."""
        with (
            patch.object(
                translator,
                "_ensure_argos_installed",
                side_effect=ImportError("argostranslate not available"),
            ),
            pytest.raises(ImportError, match="argostranslate not available"),
        ):
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
            TranslationResult("hello", "hola", "en", "es", success=True),
        ]
        output = format_translations(results)

        assert "en -> es" in output
        assert "hello" in output
        assert "hola" in output

    def test_format_multiple_translations(self) -> None:
        """Test formatting multiple translations."""
        results = [
            TranslationResult("hello", "hola", "en", "es", success=True),
            TranslationResult("world", "mundo", "en", "es", success=True),
        ]
        output = format_translations(results)

        assert "hello" in output
        assert "hola" in output
        assert "world" in output
        assert "mundo" in output

    def test_format_with_errors(self) -> None:
        """Test formatting with failed translations."""
        results = [
            TranslationResult("hello", "hola", "en", "es", success=True),
            TranslationResult(
                "xyz", "", "en", "es", success=False, error="Unknown word"
            ),
        ]
        output = format_translations(results, show_errors=True)

        assert "hello" in output
        assert "Error: Unknown word" in output

    def test_format_hide_errors(self) -> None:
        """Test formatting with errors hidden."""
        results = [
            TranslationResult("hello", "hola", "en", "es", success=True),
            TranslationResult(
                "xyz", "", "en", "es", success=False, error="Unknown word"
            ),
        ]
        output = format_translations(results, show_errors=False)

        assert "hello" in output
        assert "Unknown word" not in output
