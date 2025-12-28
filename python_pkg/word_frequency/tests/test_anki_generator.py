#!/usr/bin/env python3
"""Tests for the Anki flashcard generator."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

try:
    from python_pkg.word_frequency.anki_generator import (
        find_word_contexts,
        generate_anki_deck,
        generate_flashcards,
        get_top_n_words,
        main,
        parse_vocabulary_curve_output,
    )
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
    from python_pkg.word_frequency.anki_generator import (
        find_word_contexts,
        generate_anki_deck,
        generate_flashcards,
        get_top_n_words,
        main,
        parse_vocabulary_curve_output,
    )


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
        excerpt, words = parse_vocabulary_curve_output(sample_vocabulary_output, 1)
        assert excerpt == "the"
        assert words == [("the", 1)]

    def test_parse_length_2(self, sample_vocabulary_output: str) -> None:
        """Test parsing output for length 2."""
        excerpt, words = parse_vocabulary_curve_output(sample_vocabulary_output, 2)
        assert excerpt == "the dog"
        assert words == [("the", 1), ("dog", 2)]

    def test_parse_length_3(self, sample_vocabulary_output: str) -> None:
        """Test parsing output for length 3."""
        excerpt, words = parse_vocabulary_curve_output(sample_vocabulary_output, 3)
        assert excerpt == "the quick fox"
        assert len(words) == 3
        assert ("the", 1) in words
        assert ("quick", 3) in words
        assert ("fox", 5) in words

    def test_parse_nonexistent_length(self, sample_vocabulary_output: str) -> None:
        """Test parsing output for non-existent length."""
        excerpt, words = parse_vocabulary_curve_output(sample_vocabulary_output, 100)
        assert excerpt == ""
        assert words == []


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
            "python_pkg.word_frequency.anki_generator.translate_words_batch"
        ) as mock_translate:
            mock_translate.return_value = [
                MagicMock(success=True, source_word="hello", translated_word="hola")
            ]
            result = generate_anki_deck(
                [("hello", 1)],
                source_lang="en",
                target_lang="es",
                deck_name="TestDeck",
            )

        assert "#separator:semicolon" in result
        assert "#deck:TestDeck" in result
        assert "#html:true" in result

    def test_generates_flashcard_content(self) -> None:
        """Test that output contains flashcard data."""
        with patch(
            "python_pkg.word_frequency.anki_generator.translate_words_batch"
        ) as mock_translate:
            mock_translate.return_value = [
                MagicMock(success=True, source_word="hello", translated_word="hola"),
                MagicMock(success=True, source_word="world", translated_word="mundo"),
            ]
            result = generate_anki_deck(
                [("hello", 1), ("world", 2)],
                source_lang="en",
                target_lang="es",
            )

        # Check that words and translations are present
        assert "hello" in result
        assert "hola" in result
        assert "world" in result
        assert "mundo" in result

    def test_includes_rank(self) -> None:
        """Test that rank is included in output."""
        with patch(
            "python_pkg.word_frequency.anki_generator.translate_words_batch"
        ) as mock_translate:
            mock_translate.return_value = [
                MagicMock(success=True, source_word="test", translated_word="prueba")
            ]
            result = generate_anki_deck(
                [("test", 42)],
                source_lang="en",
                target_lang="es",
            )

        assert "#42" in result

    def test_escapes_semicolons(self) -> None:
        """Test that semicolons in words are escaped."""
        with patch(
            "python_pkg.word_frequency.anki_generator.translate_words_batch"
        ) as mock_translate:
            mock_translate.return_value = [
                MagicMock(
                    success=True, source_word="test;word", translated_word="translation"
                )
            ]
            result = generate_anki_deck(
                [("test;word", 1)],
                source_lang="en",
                target_lang="es",
            )

        # Semicolons should be replaced with commas
        assert "test,word" in result

    def test_includes_context_when_requested(self) -> None:
        """Test that context is included when requested."""
        with patch(
            "python_pkg.word_frequency.anki_generator.translate_words_batch"
        ) as mock_translate:
            mock_translate.return_value = [
                MagicMock(success=True, source_word="hello", translated_word="hola")
            ]
            contexts = {"hello": "...say hello to..."}
            result = generate_anki_deck(
                [("hello", 1)],
                source_lang="en",
                target_lang="es",
                contexts=contexts,
                include_context=True,
            )

        assert "Context" in result
        assert "say" in result

    def test_no_translate_flag(self) -> None:
        """Test that no_translate skips translation."""
        result = generate_anki_deck(
            [("hello", 1), ("world", 2)],
            source_lang="en",
            target_lang="es",
            no_translate=True,
        )

        # Should have [TODO] placeholders
        assert "[TODO]" in result
        assert "hello" in result
        assert "world" in result


# Tests for get_top_n_words


class TestGetTopNWords:
    """Tests for getting top N words."""

    def test_get_top_5_words(self) -> None:
        """Test getting top 5 words from text."""
        text = "the cat sat on the mat the cat meowed"
        words = get_top_n_words(text, 5)
        assert len(words) == 5
        # 'the' appears 3x, 'cat' appears 2x
        assert words[0][0] == "the"
        assert words[0][1] == 1
        assert words[1][0] == "cat"
        assert words[1][1] == 2

    def test_ranks_are_sequential(self) -> None:
        """Test that ranks are 1-based and sequential."""
        text = "one two three four five six seven eight"
        words = get_top_n_words(text, 8)
        ranks = [r for _, r in words]
        assert ranks == [1, 2, 3, 4, 5, 6, 7, 8]


# Tests for main function


class TestMain:
    """Tests for the main CLI function."""

    def test_missing_file_returns_error(self) -> None:
        """Test that missing file returns error code."""
        result = main(["--file", "nonexistent.txt", "--length", "10"])
        assert result == 1

    def test_help_flag(self, capsys: pytest.CaptureFixture[str]) -> None:
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
            "python_pkg.word_frequency.anki_generator.translate_words_batch"
        ) as mock_translate:
            # Mock translation to avoid network calls
            def mock_translate_fn(
                words: list[str], from_lang: str, to_lang: str
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
        self, sample_text_file: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test CLI with actual file."""
        from python_pkg.word_frequency.anki_generator import C_EXECUTABLE

        if not C_EXECUTABLE.exists():
            pytest.skip("C executable not found")

        output_file = tmp_path / "anki_output.txt"

        with patch(
            "python_pkg.word_frequency.anki_generator.translate_words_batch"
        ) as mock_translate:
            mock_translate.return_value = [
                MagicMock(success=True, source_word="the", translated_word="le")
            ]

            result = main(
                [
                    "--file",
                    str(sample_text_file),
                    "--length",
                    "1",
                    "--output",
                    str(output_file),
                ]
            )

        assert result == 0
        captured = capsys.readouterr()
        assert "FLASHCARD GENERATION COMPLETE" in captured.out


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
