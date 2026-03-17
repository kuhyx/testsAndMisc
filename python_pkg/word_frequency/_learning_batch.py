"""Batch generation helpers for the learning pipe module."""

from __future__ import annotations

from dataclasses import dataclass

from python_pkg.word_frequency._learning_constants import LessonConfig
from python_pkg.word_frequency.excerpt_finder import find_best_excerpt
import python_pkg.word_frequency.translator as _translator


def _detect_translation_language(
    text: str,
    config: LessonConfig,
    lines: list[str],
) -> tuple[str | None, str | None]:
    """Detect translation settings and return (from, to) pair."""
    actual_from = config.translate_from
    actual_to = config.translate_to or "en"

    if actual_from == "auto" or (
        config.translate_to and not config.translate_from
    ):
        detected = _translator.detect_language(text)
        if detected:
            actual_from = detected
            lines.append(f"Detected language: {detected}")
        else:
            lines.append(
                "Warning: Could not detect language "
                "(install langdetect: "
                "pip install langdetect)"
            )
            actual_from = None

    return actual_from, actual_to


def _format_word_list(
    batch_words: list[tuple[str, int]],
    start_idx: int,
    total_words: int,
    translations: dict[str, str],
) -> list[str]:
    """Format the vocabulary word list for a batch."""
    lines: list[str] = []
    for i, (word, count) in enumerate(
        batch_words, start=start_idx + 1,
    ):
        percentage = (count / total_words) * 100
        if translations:
            trans = translations.get(word, "?")
            lines.append(
                f"  {i:3}. {word:<20} -> {trans:<20}"
                f" ({count:,} occurrences, "
                f"{percentage:.2f}%)"
            )
        else:
            lines.append(
                f"  {i:3}. {word:<20}"
                f" ({count:,} occurrences, "
                f"{percentage:.2f}%)"
            )
    return lines


@dataclass(frozen=True)
class _LessonContext:
    """Shared context for batch generation."""

    text: str
    word_counts: dict[str, int]
    config: LessonConfig


def _generate_batch_section(
    ctx: _LessonContext,
    batch_num: int,
    batch_words: list[tuple[str, int]],
    cumulative_words: list[str],
) -> list[str]:
    """Generate lines for a single batch section."""
    config = ctx.config
    total_words = sum(ctx.word_counts.values())
    start_idx = batch_num * config.batch_size
    end_idx = start_idx + config.batch_size

    lines: list[str] = []
    lines.append("-" * 70)
    lines.append(
        f"BATCH {batch_num + 1}: Words "
        f"{start_idx + 1} - "
        f"{min(end_idx, start_idx + len(batch_words))}"
    )
    lines.append("-" * 70)
    lines.append("")

    # Get translations if requested
    translations: dict[str, str] = {}
    do_translate = (
        config.translate_from is not None
        and config.translate_to is not None
    )
    if do_translate:
        words_to_translate = [word for word, _ in batch_words]
        translation_results = _translator.translate_words_batch(
            words_to_translate,
            config.translate_from,  # type: ignore[arg-type]
            config.translate_to,  # type: ignore[arg-type]
        )
        translations = {
            r.source_word: r.translated_word
            for r in translation_results
            if r.success
        }

    lines.append("VOCABULARY TO LEARN:")
    lines.append("")
    lines.extend(
        _format_word_list(
            batch_words, start_idx, total_words, translations,
        )
    )
    lines.append("")

    # Cumulative coverage
    cumulative_count = sum(
        ctx.word_counts[w]
        for w in cumulative_words
        if w in ctx.word_counts
    )
    coverage = (cumulative_count / total_words) * 100
    lines.append(
        "After learning these words, "
        f"you'll recognize ~{coverage:.1f}% of the text"
    )
    lines.append("")

    # Excerpts
    lines.append("PRACTICE EXCERPTS:")
    lines.append(
        "(Excerpts where your learned vocabulary "
        "is most concentrated)"
    )
    lines.append("")

    excerpts = find_best_excerpt(
        ctx.text,
        cumulative_words,
        config.excerpt_length,
        case_sensitive=config.case_sensitive,
        top_n=config.excerpts_per_batch,
    )

    for j, excerpt in enumerate(excerpts, 1):
        lines.append(
            f"  Excerpt {j} "
            f"({excerpt.match_percentage:.1f}% known words):"
        )
        lines.append(f'  "{excerpt.excerpt}"')
        lines.append("")

    return lines
