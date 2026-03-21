"""Tests for word_frequency._generation module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from python_pkg.word_frequency._generation import (
    _detect_source_language,
    cache_deck,
    cache_excerpt,
    generate_flashcards,
    get_cached_deck,
    get_cached_excerpt,
    run_vocabulary_curve,
    run_vocabulary_curve_inverse,
)
from python_pkg.word_frequency._types import FlashcardOptions
from python_pkg.word_frequency.cache import AnkiDeckKey


class TestRunVocabularyCurve:
    """Tests for run_vocabulary_curve."""

    def test_executable_not_found(self, tmp_path: Path) -> None:
        with (
            patch(
                "python_pkg.word_frequency._generation.C_EXECUTABLE",
                tmp_path / "nonexistent",
            ),
            pytest.raises(FileNotFoundError, match="C executable not found"),
        ):
            run_vocabulary_curve(tmp_path / "text.txt", 10)

    def test_success(self, tmp_path: Path) -> None:
        exe = tmp_path / "vocab_curve"
        exe.write_text("", encoding="utf-8")
        with (
            patch("python_pkg.word_frequency._generation.C_EXECUTABLE", exe),
            patch("python_pkg.word_frequency._generation.subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(stdout="output")
            result = run_vocabulary_curve(tmp_path / "text.txt", 10)
        assert result == "output"

    def test_dump_vocab_flag(self, tmp_path: Path) -> None:
        exe = tmp_path / "vocab_curve"
        exe.write_text("", encoding="utf-8")
        with (
            patch("python_pkg.word_frequency._generation.C_EXECUTABLE", exe),
            patch("python_pkg.word_frequency._generation.subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(stdout="output")
            run_vocabulary_curve(tmp_path / "text.txt", 10, dump_vocab=True)
        cmd = mock_run.call_args[0][0]
        assert "--dump-vocab" in cmd


class TestRunVocabularyCurveInverse:
    """Tests for run_vocabulary_curve_inverse."""

    def test_executable_not_found(self, tmp_path: Path) -> None:
        with (
            patch(
                "python_pkg.word_frequency._generation.C_EXECUTABLE",
                tmp_path / "nonexistent",
            ),
            pytest.raises(FileNotFoundError, match="C executable not found"),
        ):
            run_vocabulary_curve_inverse(tmp_path / "text.txt", 100)

    def test_success(self, tmp_path: Path) -> None:
        exe = tmp_path / "vocab_curve"
        exe.write_text("", encoding="utf-8")
        with (
            patch("python_pkg.word_frequency._generation.C_EXECUTABLE", exe),
            patch("python_pkg.word_frequency._generation.subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(stdout="output")
            result = run_vocabulary_curve_inverse(tmp_path / "text.txt", 100)
        assert result == "output"

    def test_dump_vocab_flag(self, tmp_path: Path) -> None:
        exe = tmp_path / "vocab_curve"
        exe.write_text("", encoding="utf-8")
        with (
            patch("python_pkg.word_frequency._generation.C_EXECUTABLE", exe),
            patch("python_pkg.word_frequency._generation.subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(stdout="output")
            run_vocabulary_curve_inverse(tmp_path / "text.txt", 100, dump_vocab=True)
        cmd = mock_run.call_args[0][0]
        assert "--dump-vocab" in cmd


class TestCaching:
    """Tests for cache helper functions."""

    def test_get_cached_excerpt_force(self) -> None:
        result = get_cached_excerpt(Path("x.txt"), 10, force=True)
        assert result is None

    def test_get_cached_excerpt_delegates(self) -> None:
        with patch(
            "python_pkg.word_frequency._generation.get_vocab_curve_cache"
        ) as mock:
            mock.return_value.get.return_value = ("ex", [("w", 1)])
            result = get_cached_excerpt(Path("x.txt"), 10)
        assert result == ("ex", [("w", 1)])

    def test_cache_excerpt_delegates(self) -> None:
        with patch(
            "python_pkg.word_frequency._generation.get_vocab_curve_cache"
        ) as mock:
            cache_excerpt(Path("x.txt"), 10, "ex", [("w", 1)])
        mock.return_value.set.assert_called_once()

    def test_get_cached_deck_force(self) -> None:
        key = AnkiDeckKey(Path("x"), 10, "es", False, True)
        result = get_cached_deck(key, force=True)
        assert result is None

    def test_get_cached_deck_delegates(self) -> None:
        key = AnkiDeckKey(Path("x"), 10, "es", False, True)
        with patch("python_pkg.word_frequency._generation.get_anki_deck_cache") as mock:
            mock.return_value.get.return_value = ("c", "e", 2, 5)
            result = get_cached_deck(key)
        assert result == ("c", "e", 2, 5)

    def test_cache_deck_delegates(self) -> None:
        key = AnkiDeckKey(Path("x"), 10, "es", False, True)
        with patch("python_pkg.word_frequency._generation.get_anki_deck_cache") as mock:
            cache_deck(key, "content", "excerpt", 2, 5)
        mock.return_value.set.assert_called_once()


class TestDetectSourceLanguage:
    """Tests for _detect_source_language."""

    def test_detects_from_text(self) -> None:
        with patch(
            "python_pkg.word_frequency._generation.detect_language",
            return_value="en",
        ):
            result = _detect_source_language(Path("x"), "hello world")
        assert result == "en"

    def test_reads_file_when_text_empty(self, tmp_path: Path) -> None:
        fp = tmp_path / "t.txt"
        fp.write_text("hello world", encoding="utf-8")
        with patch(
            "python_pkg.word_frequency._generation.detect_language",
            return_value="en",
        ):
            result = _detect_source_language(fp, "")
        assert result == "en"

    def test_raises_when_detection_fails(self) -> None:
        with (
            patch(
                "python_pkg.word_frequency._generation.detect_language",
                return_value=None,
            ),
            pytest.raises(ValueError, match="Could not auto-detect"),
        ):
            _detect_source_language(Path("x"), "hello world")


class TestGenerateFlashcards:
    """Tests for generate_flashcards."""

    def test_cached_deck_returned(self, tmp_path: Path) -> None:
        fp = tmp_path / "t.txt"
        fp.write_text("hello", encoding="utf-8")
        with patch(
            "python_pkg.word_frequency._generation.get_cached_deck",
            return_value=("content", "excerpt", 5, 3),
        ):
            result = generate_flashcards(fp, 10)
        assert result == ("content", "excerpt", 5, 3)

    def test_full_generation(self, tmp_path: Path) -> None:
        fp = tmp_path / "t.txt"
        fp.write_text("hello world", encoding="utf-8")
        vocab_output = """[Length 5] Vocab needed: 2
  Excerpt: "hello world foo bar baz"
  Words: hello(#1), world(#2)

VOCAB_DUMP_START
hello;1
world;2
foo;3
VOCAB_DUMP_END
"""
        with (
            patch(
                "python_pkg.word_frequency._generation.get_cached_deck",
                return_value=None,
            ),
            patch(
                "python_pkg.word_frequency._generation.run_vocabulary_curve",
                return_value=vocab_output,
            ),
            patch(
                "python_pkg.word_frequency._generation.detect_language",
                return_value="en",
            ),
            patch(
                "python_pkg.word_frequency._generation.generate_anki_deck",
                return_value="deck content",
            ),
            patch(
                "python_pkg.word_frequency._generation.get_anki_deck_cache"
            ) as mock_cache,
        ):
            content, excerpt, num_words, max_rank = generate_flashcards(
                fp,
                5,
                FlashcardOptions(source_lang="en"),
            )
        assert content == "deck content"
        assert excerpt == "hello world foo bar baz"
        mock_cache.return_value.set.assert_called_once()

    def test_no_words_raises(self, tmp_path: Path) -> None:
        fp = tmp_path / "t.txt"
        fp.write_text("hello", encoding="utf-8")
        with (
            patch(
                "python_pkg.word_frequency._generation.get_cached_deck",
                return_value=None,
            ),
            patch(
                "python_pkg.word_frequency._generation.run_vocabulary_curve",
                return_value="nothing useful",
            ),
            patch(
                "python_pkg.word_frequency._generation.detect_language",
                return_value="en",
            ),
            pytest.raises(ValueError, match="No words found"),
        ):
            generate_flashcards(fp, 5, FlashcardOptions(source_lang="en"))

    def test_no_translate_skips_cache(self, tmp_path: Path) -> None:
        fp = tmp_path / "t.txt"
        fp.write_text("hello world", encoding="utf-8")
        vocab_output = """[Length 5] Vocab needed: 2
  Excerpt: "hello world foo bar baz"
  Words: hello(#1), world(#2)
"""
        with (
            patch(
                "python_pkg.word_frequency._generation.run_vocabulary_curve",
                return_value=vocab_output,
            ),
            patch(
                "python_pkg.word_frequency._generation.generate_anki_deck",
                return_value="deck",
            ),
            patch(
                "python_pkg.word_frequency._generation.get_anki_deck_cache"
            ) as mock_cache,
        ):
            generate_flashcards(
                fp,
                5,
                FlashcardOptions(source_lang="en", no_translate=True),
                all_vocab=False,
            )
        mock_cache.return_value.set.assert_not_called()

    def test_include_context(self, tmp_path: Path) -> None:
        fp = tmp_path / "t.txt"
        fp.write_text("hello world foo bar baz", encoding="utf-8")
        vocab_output = """[Length 5] Vocab needed: 2
  Excerpt: "hello world foo bar baz"
  Words: hello(#1), world(#2)
"""
        with (
            patch(
                "python_pkg.word_frequency._generation.get_cached_deck",
                return_value=None,
            ),
            patch(
                "python_pkg.word_frequency._generation.run_vocabulary_curve",
                return_value=vocab_output,
            ),
            patch(
                "python_pkg.word_frequency._generation.generate_anki_deck",
                return_value="deck",
            ),
            patch("python_pkg.word_frequency._generation.get_anki_deck_cache"),
        ):
            generate_flashcards(
                fp,
                5,
                FlashcardOptions(
                    source_lang="en",
                    include_context=True,
                    no_translate=True,
                ),
                all_vocab=False,
            )

    def test_auto_detect_language(self, tmp_path: Path) -> None:
        fp = tmp_path / "t.txt"
        fp.write_text("hello world", encoding="utf-8")
        vocab_output = """[Length 5] Vocab needed: 2
  Excerpt: "hello world foo bar baz"
  Words: hello(#1), world(#2)
"""
        with (
            patch(
                "python_pkg.word_frequency._generation.get_cached_deck",
                return_value=None,
            ),
            patch(
                "python_pkg.word_frequency._generation.run_vocabulary_curve",
                return_value=vocab_output,
            ),
            patch(
                "python_pkg.word_frequency._generation.detect_language",
                return_value="en",
            ),
            patch(
                "python_pkg.word_frequency._generation.generate_anki_deck",
                return_value="deck",
            ),
            patch("python_pkg.word_frequency._generation.get_anki_deck_cache"),
        ):
            content, excerpt, num_words, max_rank = generate_flashcards(
                fp, 5, FlashcardOptions(source_lang=None, no_translate=True)
            )
        assert content == "deck"

    def test_include_context_empty_file(self, tmp_path: Path) -> None:
        """Cover the re-read path when initial read returns empty."""
        fp = tmp_path / "t.txt"
        fp.write_text("", encoding="utf-8")
        vocab_output = """[Length 1] Vocab needed: 1
  Excerpt: "hello"
  Words: hello(#1)
"""
        with (
            patch(
                "python_pkg.word_frequency._generation.get_cached_deck",
                return_value=None,
            ),
            patch(
                "python_pkg.word_frequency._generation.run_vocabulary_curve",
                return_value=vocab_output,
            ),
            patch(
                "python_pkg.word_frequency._generation.generate_anki_deck",
                return_value="deck",
            ),
            patch("python_pkg.word_frequency._generation.get_anki_deck_cache"),
        ):
            generate_flashcards(
                fp,
                1,
                FlashcardOptions(
                    source_lang="en",
                    include_context=True,
                    no_translate=True,
                ),
                all_vocab=False,
            )
