"""Tests for _learning_batch missing branches (lines 27-28, 54-55, 104-110)."""

from __future__ import annotations

from collections import Counter
from unittest.mock import patch

from python_pkg.word_frequency._learning_batch import (
    _detect_translation_language,
    _format_word_list,
    _generate_batch_section,
    _LessonContext,
)
from python_pkg.word_frequency._learning_constants import LessonConfig
from python_pkg.word_frequency._translator_helpers import TranslationResult
import python_pkg.word_frequency.translator as _translator_module


class TestDetectTranslationLanguageFailure:
    """Cover lines 27-28: detection returns None."""

    def test_auto_detect_fails(self) -> None:
        """When detect_language returns None, actual_from is set to None."""
        config = LessonConfig(translate_from="auto", translate_to="en")
        lines: list[str] = []
        with patch.object(_translator_module, "detect_language", return_value=None):
            actual_from, actual_to = _detect_translation_language(
                "some text", config, lines
            )
        assert actual_from is None
        assert actual_to == "en"
        assert any("Could not detect" in line for line in lines)

    def test_translate_to_set_without_from_detection_fails(self) -> None:
        """Cover translate_to set, translate_from None, detection fails."""
        config = LessonConfig(translate_from=None, translate_to="es")
        lines: list[str] = []
        with patch.object(_translator_module, "detect_language", return_value=None):
            actual_from, actual_to = _detect_translation_language("text", config, lines)
        assert actual_from is None
        assert actual_to == "es"
        assert any("Could not detect" in line for line in lines)


class TestFormatWordListNoTranslations:
    """Cover lines 54-55: translations dict is empty."""

    def test_empty_translations(self) -> None:
        """When translations is empty, format without translation column."""
        batch_words = [("hello", 10), ("world", 5)]
        result = _format_word_list(
            batch_words,
            start_idx=0,
            total_words=100,
            translations={},
        )
        assert len(result) == 2
        # No "->" separator when no translations
        for line in result:
            assert "->" not in line
            assert "occurrences" in line

    def test_with_translations(self) -> None:
        """Contrast: when translations exist, should include ->."""
        batch_words = [("hello", 10)]
        result = _format_word_list(
            batch_words,
            start_idx=0,
            total_words=100,
            translations={"hello": "hola"},
        )
        assert len(result) == 1
        assert "->" in result[0]
        assert "hola" in result[0]


class TestGenerateBatchSectionWithTranslation:
    """Cover lines 104-110: do_translate is True in _generate_batch_section."""

    def _make_ctx(
        self,
        text: str = "hello hello world",
        translate_from: str | None = "en",
        translate_to: str | None = "es",
    ) -> _LessonContext:
        word_counts: dict[str, int] = Counter(text.split())
        config = LessonConfig(
            batch_size=5,
            num_batches=1,
            translate_from=translate_from,
            translate_to=translate_to,
            skip_default_stopwords=True,
        )
        return _LessonContext(
            text=text,
            word_counts=word_counts,
            config=config,
        )

    def test_translate_branch(self) -> None:
        """Cover lines 104-110: translation happens."""
        ctx = self._make_ctx()
        batch_words = [("hello", 2), ("world", 1)]
        cumulative = ["hello", "world"]

        def fake_batch(
            words: list[str],
            _from_lang: str | None,
            _to_lang: str | None,
        ) -> list[TranslationResult]:
            return [
                TranslationResult(
                    source_word=w,
                    translated_word=f"t_{w}",
                    source_lang="en",
                    target_lang="es",
                    success=True,
                )
                for w in words
            ]

        with patch.object(
            _translator_module,
            "translate_words_batch",
            side_effect=fake_batch,
        ):
            lines = _generate_batch_section(ctx, 0, batch_words, cumulative)

        combined = "\n".join(lines)
        assert "t_hello" in combined
        assert "t_world" in combined
        assert "VOCABULARY TO LEARN" in combined

    def test_no_translate_branch(self) -> None:
        """Contrast: translate_from is None → no translation."""
        ctx = self._make_ctx(translate_from=None, translate_to=None)
        batch_words = [("hello", 2)]
        cumulative = ["hello"]
        lines = _generate_batch_section(ctx, 0, batch_words, cumulative)
        combined = "\n".join(lines)
        assert "VOCABULARY TO LEARN" in combined
        # No translation column
        assert "->" not in combined or "t_" not in combined
