"""Tests for word_frequency._deck_builder module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from python_pkg.word_frequency._deck_builder import (
    _build_translation_lookup,
    _format_excerpt_card,
    find_word_contexts,
    generate_anki_deck,
)
from python_pkg.word_frequency._types import DeckInput


class TestFormatExcerptCard:
    """Tests for _format_excerpt_card."""

    def test_no_excerpt_words(self) -> None:
        result = _format_excerpt_card("hello world", None)
        assert "TARGET EXCERPT" in result
        assert "hello world" in result

    def test_same_most_freq_and_rarest(self) -> None:
        result = _format_excerpt_card("hello hello", [("hello", 1)])
        assert "<b><i>" in result

    def test_different_most_freq_and_rarest(self) -> None:
        result = _format_excerpt_card(
            "hello world",
            [("hello", 1), ("world", 5)],
        )
        assert "<b>" in result
        assert "<i>" in result

    def test_semicolons_escaped(self) -> None:
        result = _format_excerpt_card("hello;world", None)
        assert "hello,world" in result


class TestBuildTranslationLookup:
    """Tests for _build_translation_lookup."""

    def test_no_translate(self) -> None:
        result = _build_translation_lookup(
            [("hello", 1), ("world", 2)],
            "en",
            "es",
            no_translate=True,
        )
        assert result == {"hello": "[TODO]", "world": "[TODO]"}

    def test_with_translation(self) -> None:
        with patch(
            "python_pkg.word_frequency._deck_builder.translate_words_batch"
        ) as mock:
            mock.return_value = [
                MagicMock(success=True, source_word="hello", translated_word="hola"),
            ]
            result = _build_translation_lookup([("hello", 1)], "en", "es")
        assert result == {"hello": "hola"}

    def test_translation_failure(self) -> None:
        with patch(
            "python_pkg.word_frequency._deck_builder.translate_words_batch"
        ) as mock:
            mock.return_value = [
                MagicMock(success=False, source_word="xyz"),
            ]
            result = _build_translation_lookup([("xyz", 1)], "en", "es")
        assert result == {"xyz": "[xyz]"}


class TestGenerateAnkiDeck:
    """Tests for generate_anki_deck."""

    def test_with_context_empty_string(self) -> None:
        with patch(
            "python_pkg.word_frequency._deck_builder.translate_words_batch"
        ) as mock:
            mock.return_value = [
                MagicMock(success=True, source_word="hello", translated_word="hola"),
            ]
            result = generate_anki_deck(
                DeckInput(
                    words_with_ranks=[("hello", 1)],
                    source_lang="en",
                    target_lang="es",
                    contexts={"hello": ""},
                ),
                include_context=True,
            )
        assert "#columns:Front;Back;Rank;Context" in result

    def test_with_context_and_word(self) -> None:
        with patch(
            "python_pkg.word_frequency._deck_builder.translate_words_batch"
        ) as mock:
            mock.return_value = [
                MagicMock(success=True, source_word="hello", translated_word="hola"),
            ]
            result = generate_anki_deck(
                DeckInput(
                    words_with_ranks=[("hello", 1)],
                    source_lang="en",
                    target_lang="es",
                    contexts={"hello": "say hello to me"},
                ),
                include_context=True,
            )
        assert "<b>hello</b>" in result

    def test_with_context_no_contexts_dict(self) -> None:
        with patch(
            "python_pkg.word_frequency._deck_builder.translate_words_batch"
        ) as mock:
            mock.return_value = [
                MagicMock(success=True, source_word="hello", translated_word="hola"),
            ]
            result = generate_anki_deck(
                DeckInput(
                    words_with_ranks=[("hello", 1)],
                    source_lang="en",
                    target_lang="es",
                    contexts=None,
                ),
                include_context=True,
            )
        assert "hola" in result

    def test_with_excerpt(self) -> None:
        with patch(
            "python_pkg.word_frequency._deck_builder.translate_words_batch"
        ) as mock:
            mock.return_value = [
                MagicMock(success=True, source_word="hello", translated_word="hola"),
            ]
            result = generate_anki_deck(
                DeckInput(
                    words_with_ranks=[("hello", 1)],
                    source_lang="en",
                    target_lang="es",
                ),
                excerpt="hello world",
                excerpt_words=[("hello", 1), ("world", 5)],
            )
        assert "TARGET EXCERPT" in result

    def test_translation_fallback_in_card(self) -> None:
        result = generate_anki_deck(
            DeckInput(
                words_with_ranks=[("hello", 1)],
                source_lang="en",
                target_lang="es",
            ),
            no_translate=True,
        )
        assert "[TODO]" in result


class TestFindWordContexts:
    """Tests for find_word_contexts edge cases."""

    def test_word_at_start(self) -> None:
        text = "hello world foo bar"
        contexts = find_word_contexts(text, ["hello"], context_words=2)
        assert "hello" in contexts

    def test_word_at_end(self) -> None:
        text = "foo bar baz hello"
        contexts = find_word_contexts(text, ["hello"], context_words=2)
        assert "hello" in contexts

    def test_empty_text(self) -> None:
        contexts = find_word_contexts("", ["hello"])
        assert contexts == {}
