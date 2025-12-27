#!/usr/bin/env python3
"""Word frequency analyzer - analyzes text and produces word usage statistics.

Usage:
    # From raw text
    python -m python_pkg.word_frequency.analyzer --text "Hello world hello"

    # From a single file
    python -m python_pkg.word_frequency.analyzer --file path/to/file.txt

    # From multiple files
    python -m python_pkg.word_frequency.analyzer --files file1.txt file2.txt file3.txt

    # Limit output to top N words
    python -m python_pkg.word_frequency.analyzer --file text.txt --top 20

    # Case-sensitive mode
    python -m python_pkg.word_frequency.analyzer --file text.txt --case-sensitive
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


def extract_words(text: str, *, case_sensitive: bool = False) -> list[str]:
    """Extract words from text.

    Args:
        text: The input text to extract words from.
        case_sensitive: If False, convert all words to lowercase.

    Returns:
        List of words found in the text.
    """
    # Match word characters including unicode letters (for Polish, Latin, etc.)
    words = re.findall(r"\b[\w]+\b", text, re.UNICODE)

    if not case_sensitive:
        words = [word.lower() for word in words]

    return words


def analyze_text(text: str, *, case_sensitive: bool = False) -> Counter[str]:
    """Analyze text and return word counts.

    Args:
        text: The input text to analyze.
        case_sensitive: If False, treat words case-insensitively.

    Returns:
        Counter object with word frequencies.
    """
    words = extract_words(text, case_sensitive=case_sensitive)
    return Counter(words)


def read_file(filepath: str | Path) -> str:
    """Read text content from a file.

    Args:
        filepath: Path to the file to read.

    Returns:
        The text content of the file.

    Raises:
        FileNotFoundError: If the file doesn't exist.
        UnicodeDecodeError: If the file can't be decoded as UTF-8.
    """
    path = Path(filepath)
    return path.read_text(encoding="utf-8")


def read_files(filepaths: Sequence[str | Path]) -> str:
    """Read and concatenate text content from multiple files.

    Args:
        filepaths: Sequence of paths to files to read.

    Returns:
        Combined text content of all files.
    """
    texts = []
    for filepath in filepaths:
        texts.append(read_file(filepath))
    return "\n".join(texts)


def format_results(
    word_counts: Counter[str],
    *,
    top_n: int | None = None,
) -> str:
    """Format word frequency results as a table.

    Args:
        word_counts: Counter object with word frequencies.
        top_n: If provided, only show the top N words.

    Returns:
        Formatted string table with results.
    """
    total_words = sum(word_counts.values())

    if total_words == 0:
        return "No words found in input."

    # Get items sorted by frequency
    if top_n is not None:
        items = word_counts.most_common(top_n)
    else:
        items = word_counts.most_common()

    # Find the maximum width for the word column
    max_word_len = max(len(word) for word, _ in items) if items else 4
    max_word_len = max(max_word_len, 4)  # Minimum width for "Word" header

    # Find the maximum width for the count column
    max_count = max(count for _, count in items) if items else 0
    count_width = max(len(str(max_count)), 5)  # Minimum width for "Count" header

    # Build the table
    lines = []
    lines.append(f"Total words: {total_words}")
    lines.append(f"Unique words: {len(word_counts)}")
    lines.append("")

    # Header
    header = f"{'Word':<{max_word_len}}  {'Count':>{count_width}}  {'Percentage':>10}"
    lines.append(header)
    lines.append("-" * len(header))

    # Data rows
    for word, count in items:
        percentage = (count / total_words) * 100
        lines.append(f"{word:<{max_word_len}}  {count:>{count_width}}  {percentage:>9.2f}%")

    return "\n".join(lines)


def analyze_and_format(
    text: str,
    *,
    case_sensitive: bool = False,
    top_n: int | None = None,
) -> str:
    """Analyze text and return formatted results.

    Args:
        text: The input text to analyze.
        case_sensitive: If False, treat words case-insensitively.
        top_n: If provided, only show the top N words.

    Returns:
        Formatted string with word frequency analysis.
    """
    word_counts = analyze_text(text, case_sensitive=case_sensitive)
    return format_results(word_counts, top_n=top_n)


def main(argv: Sequence[str] | None = None) -> int:
    """Main entry point for the word frequency analyzer.

    Args:
        argv: Command line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    parser = argparse.ArgumentParser(
        description="Analyze word frequency in text.",
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
    input_group.add_argument(
        "--files",
        "-F",
        nargs="+",
        type=str,
        help="Paths to multiple files to analyze",
    )

    parser.add_argument(
        "--top",
        "-n",
        type=int,
        default=None,
        help="Show only the top N most frequent words",
    )
    parser.add_argument(
        "--case-sensitive",
        "-c",
        action="store_true",
        help="Treat words case-sensitively (default: case-insensitive)",
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
        elif args.file:
            text = read_file(args.file)
        else:  # args.files
            text = read_files(args.files)

        result = analyze_and_format(
            text,
            case_sensitive=args.case_sensitive,
            top_n=args.top,
        )

        if args.output:
            Path(args.output).write_text(result, encoding="utf-8")
            print(f"Output written to {args.output}")  # noqa: T201
        else:
            print(result)  # noqa: T201

    except FileNotFoundError as e:
        print(f"Error: File not found - {e}", file=sys.stderr)  # noqa: T201
        return 1
    except UnicodeDecodeError as e:
        print(f"Error: Could not decode file as UTF-8 - {e}", file=sys.stderr)  # noqa: T201
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
