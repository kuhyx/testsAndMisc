#!/usr/bin/env python3
"""Vocabulary learning curve analyzer.

Finds the minimum vocabulary needed to understand excerpts of increasing length.
For each excerpt length (1, 2, 3, ... N words), finds the excerpt that requires
the fewest top-frequency words to understand 100%.

Usage:
    python -m python_pkg.word_frequency.vocabulary_curve --file text.txt
    python -m python_pkg.word_frequency.vocabulary_curve --file text.txt --max-length 50
    python -m python_pkg.word_frequency.vocabulary_curve --text "some text here"
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from collections.abc import Sequence

try:
    from python_pkg.word_frequency.analyzer import analyze_text, read_file
except ImportError:
    from analyzer import analyze_text, read_file


class ExcerptAnalysis(NamedTuple):
    """Analysis result for an excerpt length."""

    excerpt_length: int
    min_vocab_needed: int
    best_excerpt: str
    words_needed: list[str]


def get_word_rank(word: str, ranked_words: list[str]) -> int | None:
    """Get the rank (1-indexed) of a word in the frequency list.

    Args:
        word: The word to look up.
        ranked_words: List of words sorted by frequency (most common first).

    Returns:
        1-indexed rank, or None if word not in list.
    """
    try:
        return ranked_words.index(word) + 1
    except ValueError:
        return None


def analyze_excerpt(
    excerpt_words: list[str],
    ranked_words: list[str],
) -> tuple[int, list[str]]:
    """Analyze how many top words are needed to understand an excerpt 100%.

    Args:
        excerpt_words: List of words in the excerpt.
        ranked_words: List of all words sorted by frequency (most common first).

    Returns:
        Tuple of (max_rank_needed, list_of_words_needed_sorted_by_rank).
    """
    unique_words = set(excerpt_words)
    ranks: list[tuple[int, str]] = []

    for word in unique_words:
        rank = get_word_rank(word, ranked_words)
        if rank is not None:
            ranks.append((rank, word))
        else:
            # Word not in vocabulary - would need infinite learning
            return float("inf"), []  # type: ignore[return-value]

    if not ranks:
        return 0, []

    # Sort by rank
    ranks.sort()
    max_rank = ranks[-1][0]
    words_needed = [word for _, word in ranks]

    return max_rank, words_needed


def find_optimal_excerpts(
    text: str,
    *,
    max_length: int = 30,
    case_sensitive: bool = False,
) -> list[ExcerptAnalysis]:
    """Find optimal excerpts for each length.

    For each excerpt length from 1 to max_length, finds the excerpt
    that requires the minimum number of top-frequency words to understand.

    Args:
        text: The source text to analyze.
        max_length: Maximum excerpt length to analyze.
        case_sensitive: Whether to treat words case-sensitively.

    Returns:
        List of ExcerptAnalysis for each length from 1 to max_length.
    """
    # Get word frequencies and create ranked list
    word_counts = analyze_text(text, case_sensitive=case_sensitive)
    ranked_words = [word for word, _ in word_counts.most_common()]

    # Extract all words from text (preserving order)
    import re

    all_words = re.findall(r"\b[\w]+\b", text, re.UNICODE)
    if not case_sensitive:
        all_words = [w.lower() for w in all_words]

    if not all_words:
        return []

    results: list[ExcerptAnalysis] = []

    for length in range(1, min(max_length + 1, len(all_words) + 1)):
        best_vocab_needed = float("inf")
        best_excerpt_words: list[str] = []
        best_words_needed: list[str] = []

        # Slide window through text
        for start in range(len(all_words) - length + 1):
            excerpt_words = all_words[start : start + length]
            vocab_needed, words_needed = analyze_excerpt(excerpt_words, ranked_words)

            if vocab_needed < best_vocab_needed:
                best_vocab_needed = vocab_needed
                best_excerpt_words = excerpt_words
                best_words_needed = words_needed

        if best_vocab_needed != float("inf"):
            results.append(
                ExcerptAnalysis(
                    excerpt_length=length,
                    min_vocab_needed=int(best_vocab_needed),
                    best_excerpt=" ".join(best_excerpt_words),
                    words_needed=best_words_needed,
                )
            )

    return results


def format_results(
    results: list[ExcerptAnalysis],
    *,
    show_excerpts: bool = False,
    show_words: bool = False,
) -> str:
    """Format analysis results as a table.

    Args:
        results: List of ExcerptAnalysis results.
        show_excerpts: If True, show the actual excerpt text.
        show_words: If True, show which words are needed.

    Returns:
        Formatted string with results.
    """
    if not results:
        return "No excerpts found."

    lines: list[str] = []
    lines.append("=" * 70)
    lines.append("VOCABULARY LEARNING CURVE")
    lines.append("=" * 70)
    lines.append("")
    lines.append("For each excerpt length, the minimum number of top-frequency")
    lines.append("words you need to learn to understand 100% of some excerpt.")
    lines.append("")
    lines.append("-" * 70)

    # Header
    if show_excerpts:
        lines.append(f"{'Length':>6}  {'Vocab':>5}  Excerpt")
        lines.append(f"{'------':>6}  {'-----':>5}  {'-------'}")
    else:
        lines.append(f"{'Length':>6}  {'Vocab Needed':>12}")
        lines.append(f"{'------':>6}  {'------------':>12}")

    prev_vocab = 0
    for r in results:
        # Mark increases
        marker = ""
        if r.min_vocab_needed > prev_vocab:
            marker = f" (+{r.min_vocab_needed - prev_vocab})"
        prev_vocab = r.min_vocab_needed

        if show_excerpts:
            # Truncate long excerpts
            excerpt = r.best_excerpt
            if len(excerpt) > 50:
                excerpt = excerpt[:47] + "..."
            lines.append(f"{r.excerpt_length:>6}  {r.min_vocab_needed:>5}  {excerpt}")
        else:
            lines.append(f"{r.excerpt_length:>6}  {r.min_vocab_needed:>12}{marker}")

        if show_words and r.words_needed:
            lines.append(f"        Words: {', '.join(r.words_needed)}")

    lines.append("-" * 70)
    lines.append("")

    # Summary statistics
    if results:
        final = results[-1]
        lines.append(f"To understand a {final.excerpt_length}-word excerpt,")
        lines.append(
            f"you need to learn at minimum {final.min_vocab_needed} top words."
        )

    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    """Main entry point.

    Args:
        argv: Command line arguments.

    Returns:
        Exit code.
    """
    parser = argparse.ArgumentParser(
        description="Analyze minimum vocabulary needed for excerpt lengths.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

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
        help="Path to a file to analyze",
    )

    parser.add_argument(
        "--max-length",
        "-m",
        type=int,
        default=30,
        help="Maximum excerpt length to analyze (default: 30)",
    )
    parser.add_argument(
        "--show-excerpts",
        "-e",
        action="store_true",
        help="Show the actual excerpt text for each length",
    )
    parser.add_argument(
        "--show-words",
        "-w",
        action="store_true",
        help="Show which words are needed for each excerpt",
    )
    parser.add_argument(
        "--case-sensitive",
        "-c",
        action="store_true",
        help="Treat words case-sensitively",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Output file path (default: print to stdout)",
    )

    args = parser.parse_args(argv)

    try:
        if args.text:
            text = args.text
        else:
            text = read_file(args.file)

        results = find_optimal_excerpts(
            text,
            max_length=args.max_length,
            case_sensitive=args.case_sensitive,
        )

        output = format_results(
            results,
            show_excerpts=args.show_excerpts,
            show_words=args.show_words,
        )

        if args.output:
            Path(args.output).write_text(output, encoding="utf-8")
            print(f"Output written to {args.output}")
        else:
            print(output)

    except FileNotFoundError as e:
        print(f"Error: File not found - {e}", file=sys.stderr)
        return 1
    except UnicodeDecodeError as e:
        print(f"Error: Could not decode file - {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
