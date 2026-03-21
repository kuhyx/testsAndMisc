#!/usr/bin/env python3
"""Tests for the Anki flashcard generator."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from python_pkg.word_frequency.anki_generator import (
    DeckInput,
    _clear_caches,
    _format_cache_size,
    _handle_normal_mode,
    _print_cache_stats,
    find_word_contexts,
    generate_anki_deck,
    main,
    parse_vocabulary_curve_output,
)

if TYPE_CHECKING:
    from pathlib import Path

# Test fixtures


@pytest.fixture
def sample_vocabulary_output() -> str:
    """Sample output from vocabulary_curve."""
    return """======================================================================
VOCABULARY LEARNING CURVE
======================================================================

Total words in text: 100
Unique words: 50

----------------------------------------------------------------------

[Length 1] Vocab needed: 1 (+1)
  Excerpt: "the"
  Words: the(#1)

[Length 2] Vocab needed: 2 (+1)
  Excerpt: "the dog"
  Words: the(#1), dog(#2)

[Length 3] Vocab needed: 5 (+3)
  Excerpt: "the quick fox"
  Words: the(#1), quick(#3), fox(#5)

----------------------------------------------------------------------
"""


@pytest.fixture
def sample_text_file(tmp_path: Path) -> Path:
    """Create a sample text file."""
    text = """The quick brown fox jumps over the lazy dog.
The fox was very quick and the dog was very lazy.
Quick foxes and lazy dogs are common in stories."""
    filepath = tmp_path / "sample.txt"
    filepath.write_text(text, encoding="utf-8")
    return filepath


# Tests for parse_vocabulary_curve_output


class TestParseVocabularyCurveOutput:
    """Tests for parsing vocabulary_curve output."""

    def test_parse_length_1(self, sample_vocabulary_output: str) -> None:
        """Test parsing output for length 1."""
        excerpt, excerpt_words, _all_vocab = parse_vocabulary_curve_output(
            sample_vocabulary_output, 1
        )
        assert excerpt == "the"
        assert excerpt_words == [("the", 1)]

    def test_parse_length_2(self, sample_vocabulary_output: str) -> None:
        """Test parsing output for length 2."""
        excerpt, excerpt_words, _all_vocab = parse_vocabulary_curve_output(
            sample_vocabulary_output, 2
        )
        assert excerpt == "the dog"
        assert excerpt_words == [("the", 1), ("dog", 2)]

    def test_parse_length_3(self, sample_vocabulary_output: str) -> None:
        """Test parsing output for length 3."""
        excerpt, excerpt_words, _all_vocab = parse_vocabulary_curve_output(
            sample_vocabulary_output, 3
        )
        assert excerpt == "the quick fox"
        assert len(excerpt_words) == 3
        assert ("the", 1) in excerpt_words
        assert ("quick", 3) in excerpt_words
        assert ("fox", 5) in excerpt_words

    def test_parse_nonexistent_length(self, sample_vocabulary_output: str) -> None:
        """Test parsing output for non-existent length."""
        excerpt, excerpt_words, _all_vocab = parse_vocabulary_curve_output(
            sample_vocabulary_output, 100
        )
        assert excerpt == ""
        assert excerpt_words == []

    def test_parse_vocab_dump(self) -> None:
        """Test parsing VOCAB_DUMP section."""
        output = """[Length 2] Vocab needed: 2
  Excerpt: "hello world"
  Words: hello(#1), world(#2)

VOCAB_DUMP_START
hello;1
world;2
VOCAB_DUMP_END
"""
        _excerpt, _excerpt_words, all_vocab = parse_vocabulary_curve_output(output, 2)
        assert all_vocab == [("hello", 1), ("world", 2)]


# Tests for find_word_contexts


class TestFindWordContexts:
    """Tests for finding word contexts."""

    def test_find_single_word_context(self) -> None:
        """Test finding context for a single word."""
        text = "The quick brown fox jumps over the lazy dog"
        contexts = find_word_contexts(text, ["fox"], context_words=2)
        assert "fox" in contexts
        assert "fox" in contexts["fox"].lower()

    def test_find_multiple_word_contexts(self) -> None:
        """Test finding contexts for multiple words."""
        text = "The quick brown fox jumps over the lazy dog"
        contexts = find_word_contexts(text, ["fox", "dog"], context_words=2)
        assert len(contexts) == 2
        assert "fox" in contexts
        assert "dog" in contexts

    def test_word_not_found(self) -> None:
        """Test when word is not in text."""
        text = "The quick brown fox"
        contexts = find_word_contexts(text, ["elephant"], context_words=2)
        assert "elephant" not in contexts


# Tests for generate_anki_deck


class TestGenerateAnkiDeck:
    """Tests for generating Anki deck content."""

    def test_generates_valid_header(self) -> None:
        """Test that output contains valid Anki headers."""
        with patch(
            "python_pkg.word_frequency._deck_builder.translate_words_batch"
        ) as mock_translate:
            mock_translate.return_value = [
                MagicMock(success=True, source_word="hello", translated_word="hola")
            ]
            result = generate_anki_deck(
                DeckInput(
                    words_with_ranks=[("hello", 1)],
                    source_lang="en",
                    target_lang="es",
                    deck_name="TestDeck",
                ),
            )

        assert "#separator:semicolon" in result
        assert "#deck:TestDeck" in result
        assert "#html:true" in result

    def test_generates_flashcard_content(self) -> None:
        """Test that output contains flashcard data."""
        with patch(
            "python_pkg.word_frequency._deck_builder.translate_words_batch"
        ) as mock_translate:
            mock_translate.return_value = [
                MagicMock(success=True, source_word="hello", translated_word="hola"),
                MagicMock(success=True, source_word="world", translated_word="mundo"),
            ]
            result = generate_anki_deck(
                DeckInput(
                    words_with_ranks=[("hello", 1), ("world", 2)],
                    source_lang="en",
                    target_lang="es",
                ),
            )

        # Check that words and translations are present
        assert "hello" in result
        assert "hola" in result
        assert "world" in result
        assert "mundo" in result

    def test_includes_rank(self) -> None:
        """Test that rank is included in output."""
        with patch(
            "python_pkg.word_frequency._deck_builder.translate_words_batch"
        ) as mock_translate:
            mock_translate.return_value = [
                MagicMock(success=True, source_word="test", translated_word="prueba")
            ]
            result = generate_anki_deck(
                DeckInput(
                    words_with_ranks=[("test", 42)],
                    source_lang="en",
                    target_lang="es",
                ),
            )

        assert "#42" in result

    def test_escapes_semicolons(self) -> None:
        """Test that semicolons in words are escaped."""
        with patch(
            "python_pkg.word_frequency._deck_builder.translate_words_batch"
        ) as mock_translate:
            mock_translate.return_value = [
                MagicMock(
                    success=True, source_word="test;word", translated_word="translation"
                )
            ]
            result = generate_anki_deck(
                DeckInput(
                    words_with_ranks=[("test;word", 1)],
                    source_lang="en",
                    target_lang="es",
                ),
            )

        # Semicolons should be replaced with commas
        assert "test,word" in result

    def test_includes_context_when_requested(self) -> None:
        """Test that context is included when requested."""
        with patch(
            "python_pkg.word_frequency._deck_builder.translate_words_batch"
        ) as mock_translate:
            mock_translate.return_value = [
                MagicMock(success=True, source_word="hello", translated_word="hola")
            ]
            contexts = {"hello": "...say hello to..."}
            result = generate_anki_deck(
                DeckInput(
                    words_with_ranks=[("hello", 1)],
                    source_lang="en",
                    target_lang="es",
                    contexts=contexts,
                ),
                include_context=True,
            )

        assert "Context" in result
        assert "say" in result

    def test_no_translate_flag(self) -> None:
        """Test that no_translate skips translation."""
        result = generate_anki_deck(
            DeckInput(
                words_with_ranks=[("hello", 1), ("world", 2)],
                source_lang="en",
                target_lang="es",
            ),
            no_translate=True,
        )

        # Should have [TODO] placeholders
        assert "[TODO]" in result
        assert "hello" in result
        assert "world" in result


# Tests for main function


class TestMain:
    """Tests for the main CLI function."""

    def test_missing_file_returns_error(self) -> None:
        """Test that missing file returns error code."""
        result = main(["--file", "nonexistent.txt", "--length", "10"])
        assert result == 1

    def test_help_flag(self) -> None:
        """Test that --help works."""
        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])
        assert exc_info.value.code == 0


# Integration tests


class TestIntegration:
    """Integration tests (require C executable)."""

    def test_generate_flashcards_creates_output(
        self, sample_text_file: Path, tmp_path: Path
    ) -> None:
        """Test that generate_flashcards produces output file."""
        from python_pkg.word_frequency.anki_generator import C_EXECUTABLE

        if not C_EXECUTABLE.exists():
            pytest.skip("C executable not found")

        output_file = tmp_path / "output.txt"

        with patch(
            "python_pkg.word_frequency._deck_builder.translate_words_batch"
        ) as mock_translate:
            # Mock translation to avoid network calls
            def mock_translate_fn(
                words: list[str], _from_lang: str, _to_lang: str
            ) -> list[MagicMock]:
                return [
                    MagicMock(success=True, source_word=w, translated_word=f"[{w}]")
                    for w in words
                ]

            mock_translate.side_effect = mock_translate_fn

            result = main(
                [
                    "--file",
                    str(sample_text_file),
                    "--length",
                    "5",
                    "--from",
                    "en",
                    "--output",
                    str(output_file),
                    "--quiet",
                ]
            )

        assert result == 0
        assert output_file.exists()

        content = output_file.read_text()
        assert "#separator:semicolon" in content

    def test_cli_with_sample_file(
        self, sample_text_file: Path, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test CLI with actual file."""
        import logging

        from python_pkg.word_frequency.anki_generator import C_EXECUTABLE

        if not C_EXECUTABLE.exists():
            pytest.skip("C executable not found")

        output_file = tmp_path / "anki_output.txt"

        with (
            caplog.at_level(logging.INFO),
            patch(
                "python_pkg.word_frequency._deck_builder.translate_words_batch"
            ) as mock_translate,
        ):
            mock_translate.return_value = [
                MagicMock(success=True, source_word="the", translated_word="le")
            ]

            result = main(
                [
                    "--file",
                    str(sample_text_file),
                    "--length",
                    "1",
                    "--from",
                    "en",
                    "--output",
                    str(output_file),
                ]
            )

        assert result == 0
        assert "FLASHCARD GENERATION COMPLETE" in caplog.text


class TestFormatCacheSize:
    """Tests for _format_cache_size."""

    def test_bytes(self) -> None:
        assert _format_cache_size(500) == "500 B"

    def test_kilobytes(self) -> None:
        assert _format_cache_size(2048) == "2.0 KB"

    def test_megabytes(self) -> None:
        assert _format_cache_size(2 * 1024 * 1024) == "2.0 MB"


class TestPrintCacheStats:
    """Tests for _print_cache_stats."""

    def test_prints_stats(self, caplog: pytest.LogCaptureFixture) -> None:
        with (
            caplog.at_level(logging.INFO),
            patch(
                "python_pkg.word_frequency.anki_generator.get_all_cache_stats",
                return_value={
                    "translations": {
                        "total_entries": 5,
                        "cache_size_bytes": 1024,
                    },
                },
            ),
        ):
            result = _print_cache_stats()
        assert result == 0
        assert "Cache Statistics" in caplog.text
        assert "1.0 KB" in caplog.text


class TestClearCaches:
    """Tests for _clear_caches."""

    def test_clears(self, caplog: pytest.LogCaptureFixture) -> None:
        with (
            caplog.at_level(logging.INFO),
            patch("python_pkg.word_frequency.anki_generator.clear_all_caches"),
        ):
            result = _clear_caches()
        assert result == 0
        assert "cleared" in caplog.text


class TestHandleNormalModeQuiet:
    """Tests for _handle_normal_mode quiet flag."""

    def test_quiet_mode(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        text_file = tmp_path / "source.txt"
        text_file.write_text("hello world", encoding="utf-8")
        args = MagicMock()
        args.quiet = True
        args.length = 2
        args.output = str(tmp_path / "out.txt")
        args.source_lang = "en"
        args.target_lang = "es"
        args.deck_name = None
        args.include_context = False
        args.no_translate = True
        args.force = False
        args.excerpt_words_only = False
        with (
            caplog.at_level(logging.INFO),
            patch(
                "python_pkg.word_frequency.anki_generator.generate_flashcards",
                return_value=("content", "hello world", 2, 2),
            ),
        ):
            result = _handle_normal_mode(args, text_file)
        assert result == 0
        assert "FLASHCARD GENERATION COMPLETE" not in caplog.text

    def test_verbose_excerpt_words_only(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        text_file = tmp_path / "source.txt"
        text_file.write_text("hello world", encoding="utf-8")
        args = MagicMock()
        args.quiet = False
        args.length = 2
        args.output = str(tmp_path / "out.txt")
        args.source_lang = "en"
        args.target_lang = "es"
        args.deck_name = None
        args.include_context = False
        args.no_translate = True
        args.force = False
        args.excerpt_words_only = True
        with (
            caplog.at_level(logging.INFO),
            patch(
                "python_pkg.word_frequency.anki_generator.generate_flashcards",
                return_value=("content", "hello world", 2, 2),
            ),
        ):
            result = _handle_normal_mode(args, text_file)
        assert result == 0
        assert "excerpt words only" in caplog.text
