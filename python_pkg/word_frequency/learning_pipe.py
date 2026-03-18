#!/usr/bin/env python3
r"""Learning pipe - combines word frequency analysis with excerpt finding.

Helps language learners by:

1. Analyzing a text to find the most common words
2. Finding excerpts where those common words are most prevalent
3. Creating a progressive learning experience in batches

The idea is to:
- Learn the top N most frequent words first
- Then read excerpts that are dense with those words
- Progressively learn more words and more complex excerpts

Usage::

    # Basic usage
    python -m python_pkg.word_frequency.learning_pipe \\
        --file text.txt

    # Custom batch size and excerpt length
    python -m python_pkg.word_frequency.learning_pipe \\
        --file text.txt --batch-size 30 --excerpt-length 50

    # Multiple batches for progressive learning
    python -m python_pkg.word_frequency.learning_pipe \\
        --file text.txt --batches 5 --batch-size 20

    # Output to file
    python -m python_pkg.word_frequency.learning_pipe \\
        --file text.txt --output lesson.txt

    # Skip common words using a stopwords file
    python -m python_pkg.word_frequency.learning_pipe \\
        --file text.txt --stopwords stopwords.txt
"""

from __future__ import annotations

import argparse
from dataclasses import replace as _replace_dc
import logging
from pathlib import Path
import sys
from typing import TYPE_CHECKING

from python_pkg.word_frequency._learning_batch import (
    _detect_translation_language,
    _generate_batch_section,
    _LessonContext,
)
from python_pkg.word_frequency._learning_constants import (
    LessonConfig,
    _resolve_stopwords,
    load_stopwords,
)
from python_pkg.word_frequency.analyzer import analyze_text, read_file

if TYPE_CHECKING:
    from collections.abc import Sequence

logger = logging.getLogger(__name__)


def generate_learning_lesson(
    text: str,
    config: LessonConfig | None = None,
) -> str:
    """Generate a learning lesson from text.

    Args:
        text: The source text to analyze.
        config: Lesson configuration. Uses defaults if None.

    Returns:
        Formatted learning lesson as a string.
    """
    if config is None:
        config = LessonConfig()

    all_stopwords = _resolve_stopwords(config)
    word_counts = analyze_text(
        text,
        case_sensitive=config.case_sensitive,
    )

    filtered_words = [
        (word, count)
        for word, count in word_counts.most_common()
        if word.lower() not in all_stopwords
        and len(word) > 1
        and not (config.skip_numbers and word.isdigit())
    ]

    total_words = sum(word_counts.values())
    lines: list[str] = []

    lines.append("=" * 70)
    lines.append("LANGUAGE LEARNING LESSON")
    lines.append("=" * 70)
    lines.append(
        f"Source text: {total_words:,} total words, "
        f"{len(word_counts):,} unique words"
    )
    if all_stopwords:
        lines.append(
            f"After filtering {len(all_stopwords)} "
            f"stopwords: {len(filtered_words):,} "
            "vocabulary words"
        )
    else:
        lines.append(
            f"Vocabulary words: {len(filtered_words):,}",
        )

    actual_from, actual_to = _detect_translation_language(
        text,
        config,
        lines,
    )
    do_translate = actual_from is not None and actual_to is not None
    if do_translate:
        lines.append(
            f"Translation: {actual_from} -> {actual_to}",
        )
    lines.append("")

    # Create resolved config with detected translation
    resolved_config = _replace_dc(
        config,
        translate_from=actual_from,
        translate_to=actual_to,
    )
    ctx = _LessonContext(
        text=text,
        word_counts=word_counts,
        config=resolved_config,
    )

    cumulative_words: list[str] = []
    for batch_num in range(config.num_batches):
        start_idx = batch_num * config.batch_size
        end_idx = start_idx + config.batch_size
        if start_idx >= len(filtered_words):
            break

        batch_words = filtered_words[start_idx:end_idx]
        cumulative_words.extend(word for word, _ in batch_words)

        lines.extend(
            _generate_batch_section(
                ctx,
                batch_num,
                batch_words,
                cumulative_words,
            )
        )

    # Summary
    lines.append("=" * 70)
    lines.append("SUMMARY")
    lines.append("=" * 70)

    if cumulative_words:
        final_coverage = sum(
            word_counts[w] for w in cumulative_words if w in word_counts
        )
        final_pct = (final_coverage / total_words) * 100
        lines.append("Total vocabulary words learned: " f"{len(cumulative_words)}")
        lines.append(f"Text coverage: {final_pct:.1f}%")
        lines.append("")
        lines.append("TIP: Focus on understanding the excerpts " "first, then read")
        lines.append("more of the original text as your " "vocabulary grows!")

    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    """Main entry point for the learning pipe.

    Args:
        argv: Command line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    parser = argparse.ArgumentParser(
        description="Generate language learning lessons from text.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Input source
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--text",
        "-t",
        type=str,
        help="Raw text to analyze",
    )
    input_group.add_argument(
        "--file",
        "-f",
        type=str,
        help="Path to a text file to analyze",
    )

    # Learning parameters
    parser.add_argument(
        "--batch-size",
        "-b",
        type=int,
        default=20,
        help="Number of words per learning batch (default: 20)",
    )
    parser.add_argument(
        "--batches",
        "-n",
        type=int,
        default=1,
        help="Number of batches to generate (default: 1)",
    )
    parser.add_argument(
        "--excerpt-length",
        "-l",
        type=int,
        default=30,
        help="Length of excerpts in words (default: 30)",
    )
    parser.add_argument(
        "--excerpts-per-batch",
        "-e",
        type=int,
        default=3,
        help="Number of excerpts per batch (default: 3)",
    )

    # Filtering options
    parser.add_argument(
        "--stopwords",
        "-s",
        type=str,
        help="Path to custom stopwords file (one word per line)",
    )
    parser.add_argument(
        "--no-default-stopwords",
        action="store_true",
        help="Don't filter out default English stopwords",
    )
    parser.add_argument(
        "--case-sensitive",
        "-c",
        action="store_true",
        help="Treat words case-sensitively",
    )
    parser.add_argument(
        "--include-numbers",
        action="store_true",
        help="Include numeric words in vocabulary (filtered by default)",
    )

    # Translation options (enabled by default)
    parser.add_argument(
        "--no-translate",
        "-T",
        action="store_true",
        help="Disable translation",
    )
    parser.add_argument(
        "--translate-from",
        type=str,
        metavar="LANG",
        help=("Source language code (e.g., 'la', 'pl'). " "If omitted, auto-detected."),
    )
    parser.add_argument(
        "--translate-to",
        type=str,
        metavar="LANG",
        default="en",
        help="Target language code (default: 'en')",
    )

    # Output options
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Output file path (default: print to stdout)",
    )

    args = parser.parse_args(argv)

    try:
        text = args.text or read_file(args.file)

        # Load custom stopwords if provided
        custom_stopwords = load_stopwords(args.stopwords)

        # Determine translation settings
        translate_from: str | None = None
        translate_to: str | None = None

        if not args.no_translate:
            translate_from = args.translate_from or "auto"
            translate_to = args.translate_to

        config = LessonConfig(
            batch_size=args.batch_size,
            num_batches=args.batches,
            excerpt_length=args.excerpt_length,
            excerpts_per_batch=args.excerpts_per_batch,
            stopwords=custom_stopwords,
            skip_default_stopwords=args.no_default_stopwords,
            skip_numbers=not args.include_numbers,
            case_sensitive=args.case_sensitive,
            translate_from=translate_from,
            translate_to=translate_to,
        )
        lesson = generate_learning_lesson(text, config)

        # Output
        if args.output:
            Path(args.output).write_text(
                lesson,
                encoding="utf-8",
            )
            logger.info(
                "Lesson written to %s",
                args.output,
            )
        else:
            logger.info(lesson)

    except FileNotFoundError:
        logger.exception("Error: File not found")
        return 1
    except UnicodeDecodeError:
        logger.exception(
            "Error: Could not decode file as UTF-8",
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
