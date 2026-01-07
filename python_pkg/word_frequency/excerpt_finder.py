#!/usr/bin/env python3
"""Excerpt finder - finds text excerpts where target words are most prevalent.

Given a text and a list of target words, this tool finds the excerpt of a
specified length (in words) where the target words appear most frequently.

Usage:
    # From raw text with target words
    python -m python_pkg.word_frequency.excerpt_finder --text "they went somewhere he and she and the guy" --words and the --length 3

    # From a file
    python -m python_pkg.word_frequency.excerpt_finder --file path/to/file.txt --words the and of --length 10

    # Target words from a file (one word per line)
    python -m python_pkg.word_frequency.excerpt_finder --file text.txt --words-file targets.txt --length 20

    # Show top N excerpts instead of just the best one
    python -m python_pkg.word_frequency.excerpt_finder --file text.txt --words the and --length 10 --top 5
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import TYPE_CHECKING, NamedTuple

try:
    from python_pkg.word_frequency.analyzer import extract_words, read_file
except ModuleNotFoundError:
    from analyzer import extract_words, read_file  # type: ignore[import-not-found]

if TYPE_CHECKING:
    from collections.abc import Sequence


class ExcerptResult(NamedTuple):
    """Result of an excerpt search."""

    excerpt: str
    words: list[str]
    start_index: int
    end_index: int
    match_count: int
    match_percentage: float


def find_best_excerpt(
    text: str,
    target_words: Sequence[str],
    excerpt_length: int,
    *,
    case_sensitive: bool = False,
    top_n: int = 1,
) -> list[ExcerptResult]:
    """Find the excerpt(s) where target words are most prevalent.

    Args:
        text: The input text to search.
        target_words: Words to search for in the excerpt.
        excerpt_length: Length of the excerpt in words.
        case_sensitive: If False, match words case-insensitively.
        top_n: Number of top excerpts to return.

    Returns:
        List of ExcerptResult with the best excerpt(s) found.
    """
    if excerpt_length <= 0:
        return []

    # Extract words with positions preserved
    words = extract_words(text, case_sensitive=case_sensitive)

    if not words or len(words) < excerpt_length:
        return []

    # Normalize target words for matching
    if case_sensitive:
        target_set = set(target_words)
    else:
        target_set = {w.lower() for w in target_words}

    # Use sliding window to find the best excerpt
    results: list[
        tuple[int, int, float, int]
    ] = []  # (match_count, -start, percentage, start)

    # Count matches in first window
    current_matches = sum(1 for w in words[:excerpt_length] if w in target_set)

    # Store first window result
    percentage = (current_matches / excerpt_length) * 100
    results.append((current_matches, 0, percentage, 0))

    # Slide the window
    for i in range(1, len(words) - excerpt_length + 1):
        # Remove the word leaving the window
        leaving_word = words[i - 1]
        if leaving_word in target_set:
            current_matches -= 1

        # Add the word entering the window
        entering_word = words[i + excerpt_length - 1]
        if entering_word in target_set:
            current_matches += 1

        percentage = (current_matches / excerpt_length) * 100
        results.append((current_matches, -i, percentage, i))

    # Sort by match count (desc), then by position (asc for tie-breaking)
    results.sort(key=lambda x: (x[0], x[1]), reverse=True)

    # Build ExcerptResult objects for top N
    output: list[ExcerptResult] = []
    seen_excerpts: set[tuple[str, ...]] = set()

    for match_count, _, percentage, start_idx in results:
        if len(output) >= top_n:
            break

        end_idx = start_idx + excerpt_length
        excerpt_words = words[start_idx:end_idx]
        excerpt_tuple = tuple(excerpt_words)

        # Skip duplicate excerpts
        if excerpt_tuple in seen_excerpts:
            continue
        seen_excerpts.add(excerpt_tuple)

        output.append(
            ExcerptResult(
                excerpt=" ".join(excerpt_words),
                words=list(excerpt_words),
                start_index=start_idx,
                end_index=end_idx,
                match_count=match_count,
                match_percentage=percentage,
            )
        )

    return output


def find_best_excerpt_with_context(
    text: str,
    target_words: Sequence[str],
    excerpt_length: int,
    *,
    case_sensitive: bool = False,
    top_n: int = 1,
    context_words: int = 0,
) -> list[ExcerptResult]:
    """Find the excerpt(s) with optional surrounding context.

    Args:
        text: The input text to search.
        target_words: Words to search for in the excerpt.
        excerpt_length: Length of the excerpt in words.
        case_sensitive: If False, match words case-insensitively.
        top_n: Number of top excerpts to return.
        context_words: Number of words to include before/after the excerpt.

    Returns:
        List of ExcerptResult with context included in the excerpt.
    """
    base_results = find_best_excerpt(
        text,
        target_words,
        excerpt_length,
        case_sensitive=case_sensitive,
        top_n=top_n,
    )

    if context_words <= 0:
        return base_results

    # Re-extract all words to get context
    all_words = extract_words(text, case_sensitive=case_sensitive)

    expanded_results: list[ExcerptResult] = []
    for result in base_results:
        # Expand the excerpt with context
        ctx_start = max(0, result.start_index - context_words)
        ctx_end = min(len(all_words), result.end_index + context_words)
        context_excerpt_words = all_words[ctx_start:ctx_end]

        expanded_results.append(
            ExcerptResult(
                excerpt=" ".join(context_excerpt_words),
                words=context_excerpt_words,
                start_index=ctx_start,
                end_index=ctx_end,
                match_count=result.match_count,
                match_percentage=result.match_percentage,
            )
        )

    return expanded_results


def format_excerpt_results(
    results: list[ExcerptResult],
    target_words: Sequence[str],
) -> str:
    """Format excerpt results for display.

    Args:
        results: List of ExcerptResult to format.
        target_words: The target words that were searched for.

    Returns:
        Formatted string with results.
    """
    if not results:
        return "No excerpts found."

    lines: list[str] = []
    lines.append(f"Target words: {', '.join(target_words)}")
    lines.append("")

    for i, result in enumerate(results, 1):
        if len(results) > 1:
            lines.append(f"=== Result #{i} ===")
        lines.append(f'Excerpt: "{result.excerpt}"')
        lines.append(f"Word position: {result.start_index} - {result.end_index - 1}")
        lines.append(
            f"Matches: {result.match_count}/{len(result.words)} ({result.match_percentage:.2f}%)"
        )
        lines.append("")

    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    """Main entry point for the excerpt finder.

    Args:
        argv: Command line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    parser = argparse.ArgumentParser(
        description="Find text excerpts where target words are most prevalent.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Input source
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--text",
        "-t",
        type=str,
        help="Raw text to search",
    )
    input_group.add_argument(
        "--file",
        "-f",
        type=str,
        help="Path to a file to search",
    )

    # Target words source
    words_group = parser.add_mutually_exclusive_group(required=True)
    words_group.add_argument(
        "--words",
        "-w",
        nargs="+",
        type=str,
        help="Target words to find",
    )
    words_group.add_argument(
        "--words-file",
        "-W",
        type=str,
        help="Path to file with target words (one per line)",
    )

    # Excerpt parameters
    parser.add_argument(
        "--length",
        "-l",
        type=int,
        required=True,
        help="Length of excerpt in words",
    )
    parser.add_argument(
        "--top",
        "-n",
        type=int,
        default=1,
        help="Show top N excerpts (default: 1)",
    )
    parser.add_argument(
        "--context",
        "-c",
        type=int,
        default=0,
        help="Number of context words before/after excerpt",
    )
    parser.add_argument(
        "--case-sensitive",
        "-s",
        action="store_true",
        help="Match words case-sensitively",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Output file path (default: print to stdout)",
    )

    args = parser.parse_args(argv)

    try:
        # Get input text
        if args.text:
            text = args.text
        else:
            text = read_file(args.file)

        # Get target words
        if args.words:
            target_words = args.words
        else:
            words_content = read_file(args.words_file)
            target_words = [w.strip() for w in words_content.splitlines() if w.strip()]

        if not target_words:
            print("Error: No target words provided", file=sys.stderr)
            return 1

        # Find excerpts
        results = find_best_excerpt_with_context(
            text,
            target_words,
            args.length,
            case_sensitive=args.case_sensitive,
            top_n=args.top,
            context_words=args.context,
        )

        # Format and print results
        output = format_excerpt_results(results, target_words)

        if args.output:
            Path(args.output).write_text(output, encoding="utf-8")
            print(f"Output written to {args.output}")
        else:
            print(output)

    except FileNotFoundError as e:
        print(f"Error: File not found - {e}", file=sys.stderr)
        return 1
    except UnicodeDecodeError as e:
        print(f"Error: Could not decode file as UTF-8 - {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
