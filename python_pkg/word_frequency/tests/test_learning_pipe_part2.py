"""Tests for learning_pipe missing line 123 (do_translate True branch)."""

from __future__ import annotations

from unittest.mock import patch

from python_pkg.word_frequency._learning_constants import LessonConfig
from python_pkg.word_frequency._translator_helpers import TranslationResult
from python_pkg.word_frequency.learning_pipe import generate_learning_lesson
import python_pkg.word_frequency.translator as _translator_module


class TestDoTranslateBranch:
    """Cover line 123: do_translate is True adds 'Translation:' line."""

    def test_translate_line_appears(self) -> None:
        """When translate_from and translate_to resolve non-None, cover line 123."""

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
            result = generate_learning_lesson(
                "hello hello hello world world test",
                LessonConfig(
                    batch_size=5,
                    num_batches=1,
                    skip_default_stopwords=True,
                    translate_from="en",
                    translate_to="es",
                ),
            )

        assert "Translation: en -> es" in result

    def test_auto_detect_translation(self) -> None:
        """Cover auto-detection resolving to non-None from language."""

        def fake_batch(
            words: list[str],
            from_lang: str | None,
            to_lang: str | None,
        ) -> list[TranslationResult]:
            return [
                TranslationResult(
                    source_word=w,
                    translated_word=f"t_{w}",
                    source_lang=from_lang,
                    target_lang=to_lang,
                    success=True,
                )
                for w in words
            ]

        with (
            patch.object(
                _translator_module,
                "detect_language",
                return_value="pl",
            ),
            patch.object(
                _translator_module,
                "translate_words_batch",
                side_effect=fake_batch,
            ),
        ):
            result = generate_learning_lesson(
                "hello hello hello world world test",
                LessonConfig(
                    batch_size=5,
                    num_batches=1,
                    skip_default_stopwords=True,
                    translate_from="auto",
                    translate_to="en",
                ),
            )

        assert "Translation: pl -> en" in result
        assert "Detected language: pl" in result
