"""Tests for _generation.generate_flashcards_inverse (lines 323-379)."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from python_pkg.word_frequency._generation import generate_flashcards_inverse
from python_pkg.word_frequency._types import FlashcardOptions

if TYPE_CHECKING:
    from pathlib import Path

_GEN = "python_pkg.word_frequency._generation"


class TestGenerateFlashcardsInverse:
    """Tests for generate_flashcards_inverse."""

    def test_basic_flow(self, tmp_path: Path) -> None:
        """Cover the happy path through all branches."""
        fp = tmp_path / "t.txt"
        fp.write_text("hello world", encoding="utf-8")
        inverse_output = (
            "INVERSE_MODE\n"
            "Longest excerpt: 5 words\n"
            'Excerpt: "hello world foo bar baz"\n'
            "Max rank used: 3\n"
            "\nVOCAB_DUMP_START\nhello;1\nworld;2\nfoo;3\nVOCAB_DUMP_END\n"
        )
        with (
            patch(
                f"{_GEN}.run_vocabulary_curve_inverse",
                return_value=inverse_output,
            ),
            patch(
                f"{_GEN}.parse_inverse_mode_output",
                return_value=(
                    "hello world foo bar baz",
                    5,
                    3,
                    [("hello", 1), ("world", 2), ("foo", 3)],
                ),
            ),
            patch(
                f"{_GEN}.detect_language",
                return_value="en",
            ),
            patch(
                f"{_GEN}.generate_anki_deck",
                return_value="deck content",
            ),
        ):
            content, excerpt, length, n_words, max_rank = generate_flashcards_inverse(
                fp,
                3,
                FlashcardOptions(source_lang="en"),
            )
        assert content == "deck content"
        assert excerpt == "hello world foo bar baz"
        assert length == 5
        assert n_words == 3
        assert max_rank == 3

    def test_default_options(self, tmp_path: Path) -> None:
        """Cover options=None branch (line 323)."""
        fp = tmp_path / "t.txt"
        fp.write_text("hello world", encoding="utf-8")
        with (
            patch(
                f"{_GEN}.run_vocabulary_curve_inverse",
                return_value="out",
            ),
            patch(
                f"{_GEN}.parse_inverse_mode_output",
                return_value=(
                    "hello world",
                    2,
                    2,
                    [("hello", 1), ("world", 2)],
                ),
            ),
            patch(
                f"{_GEN}.detect_language",
                return_value="en",
            ),
            patch(
                f"{_GEN}.generate_anki_deck",
                return_value="deck",
            ),
        ):
            result = generate_flashcards_inverse(fp, 2)
        assert result[0] == "deck"

    def test_excerpt_length_zero_raises(self, tmp_path: Path) -> None:
        """Cover the excerpt_length == 0 ValueError branch."""
        fp = tmp_path / "t.txt"
        fp.write_text("text", encoding="utf-8")
        with (
            patch(
                f"{_GEN}.run_vocabulary_curve_inverse",
                return_value="out",
            ),
            patch(
                f"{_GEN}.parse_inverse_mode_output",
                return_value=("", 0, 0, []),
            ),
            pytest.raises(ValueError, match="No valid excerpt found"),
        ):
            generate_flashcards_inverse(fp, 5, FlashcardOptions(source_lang="en"))

    def test_no_vocab_words_raises(self, tmp_path: Path) -> None:
        """Cover the 'not all_vocab_words' ValueError branch."""
        fp = tmp_path / "t.txt"
        fp.write_text("text", encoding="utf-8")
        with (
            patch(
                f"{_GEN}.run_vocabulary_curve_inverse",
                return_value="out",
            ),
            patch(
                f"{_GEN}.parse_inverse_mode_output",
                return_value=("hello", 1, 1, []),
            ),
            pytest.raises(ValueError, match="No vocabulary returned"),
        ):
            generate_flashcards_inverse(fp, 5, FlashcardOptions(source_lang="en"))

    def test_include_context(self, tmp_path: Path) -> None:
        """Cover include_context=True path (context generation)."""
        fp = tmp_path / "t.txt"
        fp.write_text("hello world foo", encoding="utf-8")
        with (
            patch(
                f"{_GEN}.run_vocabulary_curve_inverse",
                return_value="out",
            ),
            patch(
                f"{_GEN}.parse_inverse_mode_output",
                return_value=(
                    "hello world",
                    2,
                    2,
                    [("hello", 1), ("world", 2)],
                ),
            ),
            patch(
                f"{_GEN}.detect_language",
                return_value="en",
            ),
            patch(
                f"{_GEN}.find_word_contexts",
                return_value={"hello": "...hello..."},
            ) as mock_ctx,
            patch(
                f"{_GEN}.generate_anki_deck",
                return_value="deck",
            ),
        ):
            generate_flashcards_inverse(
                fp,
                2,
                FlashcardOptions(
                    source_lang="en",
                    include_context=True,
                ),
            )
        mock_ctx.assert_called_once()

    def test_include_context_rereads_when_empty(self, tmp_path: Path) -> None:
        """Cover the 'if not text' re-read branch inside context."""
        fp = tmp_path / "t.txt"
        fp.write_text("", encoding="utf-8")
        with (
            patch(
                f"{_GEN}.run_vocabulary_curve_inverse",
                return_value="out",
            ),
            patch(
                f"{_GEN}.parse_inverse_mode_output",
                return_value=(
                    "hello",
                    1,
                    1,
                    [("hello", 1)],
                ),
            ),
            patch(
                f"{_GEN}.generate_anki_deck",
                return_value="deck",
            ),
            patch(f"{_GEN}.find_word_contexts", return_value={}),
            patch(f"{_GEN}.read_file", return_value="") as mock_read,
        ):
            generate_flashcards_inverse(
                fp,
                1,
                FlashcardOptions(
                    source_lang="en",
                    include_context=True,
                ),
            )
        # read_file called twice: once for initial text, once for context
        assert mock_read.call_count == 2

    def test_auto_detect_language(self, tmp_path: Path) -> None:
        """Cover source_lang=None auto-detection path."""
        fp = tmp_path / "t.txt"
        fp.write_text("hola mundo", encoding="utf-8")
        with (
            patch(
                f"{_GEN}.run_vocabulary_curve_inverse",
                return_value="out",
            ),
            patch(
                f"{_GEN}.parse_inverse_mode_output",
                return_value=(
                    "hola mundo",
                    2,
                    2,
                    [("hola", 1), ("mundo", 2)],
                ),
            ),
            patch(
                f"{_GEN}.detect_language",
                return_value="es",
            ) as mock_detect,
            patch(
                f"{_GEN}.generate_anki_deck",
                return_value="deck",
            ),
        ):
            generate_flashcards_inverse(fp, 2, FlashcardOptions(source_lang=None))
        mock_detect.assert_called_once()

    def test_custom_deck_name(self, tmp_path: Path) -> None:
        """Cover deck_name from options."""
        fp = tmp_path / "t.txt"
        fp.write_text("hello", encoding="utf-8")
        with (
            patch(
                f"{_GEN}.run_vocabulary_curve_inverse",
                return_value="out",
            ),
            patch(
                f"{_GEN}.parse_inverse_mode_output",
                return_value=(
                    "hello",
                    1,
                    1,
                    [("hello", 1)],
                ),
            ),
            patch(
                f"{_GEN}.generate_anki_deck",
                return_value="deck",
            ) as mock_deck,
        ):
            generate_flashcards_inverse(
                fp,
                1,
                FlashcardOptions(
                    source_lang="en",
                    deck_name="MyDeck",
                ),
            )
        call_kwargs = mock_deck.call_args
        deck_input = call_kwargs[0][0]
        assert deck_input.deck_name == "MyDeck"

    def test_default_deck_name(self, tmp_path: Path) -> None:
        """Cover auto-generated deck_name when none provided."""
        fp = tmp_path / "sample.txt"
        fp.write_text("hello", encoding="utf-8")
        with (
            patch(
                f"{_GEN}.run_vocabulary_curve_inverse",
                return_value="out",
            ),
            patch(
                f"{_GEN}.parse_inverse_mode_output",
                return_value=(
                    "hello",
                    1,
                    1,
                    [("hello", 1)],
                ),
            ),
            patch(
                f"{_GEN}.generate_anki_deck",
                return_value="deck",
            ) as mock_deck,
        ):
            generate_flashcards_inverse(
                fp,
                5,
                FlashcardOptions(source_lang="en", deck_name=None),
            )
        deck_input = mock_deck.call_args[0][0]
        assert deck_input.deck_name == "sample_top5"

    def test_excerpt_words_filtering(self, tmp_path: Path) -> None:
        """Cover the excerpt_words filtering logic."""
        fp = tmp_path / "t.txt"
        fp.write_text("hello world", encoding="utf-8")
        with (
            patch(
                f"{_GEN}.run_vocabulary_curve_inverse",
                return_value="out",
            ),
            patch(
                f"{_GEN}.parse_inverse_mode_output",
                return_value=(
                    "hello",
                    1,
                    2,
                    [("hello", 1), ("world", 2), ("foo", 3)],
                ),
            ),
            patch(
                f"{_GEN}.generate_anki_deck",
                return_value="deck",
            ) as mock_deck,
        ):
            generate_flashcards_inverse(fp, 3, FlashcardOptions(source_lang="en"))
        call_kwargs = mock_deck.call_args
        excerpt_words = call_kwargs[1]["excerpt_words"]
        # Only "hello" is in the excerpt, not "world" or "foo"
        assert len(excerpt_words) == 1
        assert excerpt_words[0][0] == "hello"

    def test_no_translate(self, tmp_path: Path) -> None:
        """Cover no_translate option."""
        fp = tmp_path / "t.txt"
        fp.write_text("text", encoding="utf-8")
        with (
            patch(
                f"{_GEN}.run_vocabulary_curve_inverse",
                return_value="out",
            ),
            patch(
                f"{_GEN}.parse_inverse_mode_output",
                return_value=(
                    "hello",
                    1,
                    1,
                    [("hello", 1)],
                ),
            ),
            patch(
                f"{_GEN}.generate_anki_deck",
                return_value="deck",
            ) as mock_deck,
        ):
            generate_flashcards_inverse(
                fp,
                1,
                FlashcardOptions(
                    source_lang="en",
                    no_translate=True,
                ),
            )
        assert mock_deck.call_args[1]["no_translate"] is True
