#!/usr/bin/env python3
"""Anki flashcard generator from vocabulary curve analysis.

Generates Anki-compatible flashcard decks from the vocabulary needed to
understand excerpts of a given length.

Usage::

    # Generate flashcards for a 20-word excerpt
    python -m python_pkg.word_frequency.anki_generator \
        --file text.txt --length 20

    # Specify source language (auto-detected by default)
    python -m python_pkg.word_frequency.anki_generator \
        --file text.txt --length 20 --from pl

    # Custom output file
    python -m python_pkg.word_frequency.anki_generator \
        --file text.txt --length 20 --output polish_vocab.txt

    # Include example sentences/context
    python -m python_pkg.word_frequency.anki_generator \
        --file text.txt --length 20 --include-context

Output:
    Creates a semicolon-separated text file importable into Anki.
    Format: ``word;translation;frequency_rank;example_context``
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
import subprocess
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

from python_pkg.word_frequency._deck_builder import (
    find_word_contexts,
    generate_anki_deck,
)
from python_pkg.word_frequency._generation import (
    cache_deck,
    cache_excerpt,
    generate_flashcards,
    generate_flashcards_inverse,
    get_cached_deck,
    get_cached_excerpt,
    run_vocabulary_curve,
    run_vocabulary_curve_inverse,
)
from python_pkg.word_frequency._parsing import (
    parse_inverse_mode_output,
    parse_vocabulary_curve_output,
)
from python_pkg.word_frequency._types import (
    _ONE_KB,
    _ONE_MB,
    C_EXECUTABLE,
    DeckInput,
    FlashcardOptions,
    VocabWord,
)
from python_pkg.word_frequency.cache import (
    clear_all_caches,
    get_all_cache_stats,
)

logger = logging.getLogger(__name__)

# Re-export public API from helper modules
__all__ = [
    "C_EXECUTABLE",
    "DeckInput",
    "FlashcardOptions",
    "VocabWord",
    "cache_deck",
    "cache_excerpt",
    "find_word_contexts",
    "generate_anki_deck",
    "generate_flashcards",
    "generate_flashcards_inverse",
    "get_cached_deck",
    "get_cached_excerpt",
    "main",
    "parse_inverse_mode_output",
    "parse_vocabulary_curve_output",
    "run_vocabulary_curve",
    "run_vocabulary_curve_inverse",
]


def _format_cache_size(value: int) -> str:
    """Format a byte size as human-readable string."""
    if value < _ONE_KB:
        return f"{value} B"
    if value < _ONE_MB:
        return f"{value / _ONE_KB:.1f} KB"
    return f"{value / _ONE_MB:.1f} MB"


def _print_cache_stats() -> int:
    """Print cache statistics and return exit code."""
    stats = get_all_cache_stats()
    logger.info("Cache Statistics")
    logger.info("=" * 50)
    for cache_name, cache_stats in stats.items():
        logger.info("\n%s:", cache_name.upper())
        for key, value in cache_stats.items():
            if key == "cache_size_bytes":
                logger.info("  %s: %s", key, _format_cache_size(value))
            else:
                logger.info("  %s: %s", key, value)
    return 0


def _clear_caches() -> int:
    """Clear all caches and return exit code."""
    clear_all_caches()
    logger.info("All caches cleared.")
    return 0


def _log_anki_import_instructions(output_path: Path) -> None:
    """Log Anki import instructions."""
    logger.info("")
    logger.info("To import into Anki:")
    logger.info("  1. Open Anki")
    logger.info("  2. File -> Import")
    logger.info("  3. Select: %s", output_path)
    logger.info("  4. Click Import")


def _handle_inverse_mode(
    args: argparse.Namespace,
    filepath: Path,
) -> int:
    """Handle inverse mode (--max-vocab) flashcard generation.

    Args:
        args: Parsed command line arguments.
        filepath: Path to source file.

    Returns:
        Exit code.
    """
    if not args.quiet:
        logger.info("Analyzing %s...", filepath.name)
        logger.info(
            "Finding longest excerpt using top %d words...",
            args.max_vocab,
        )

    anki_content, excerpt, excerpt_length, num_words, max_rank_used = (
        generate_flashcards_inverse(
            filepath,
            args.max_vocab,
            FlashcardOptions(
                source_lang=args.source_lang,
                target_lang=args.target_lang,
                deck_name=args.deck_name,
                include_context=args.include_context,
                no_translate=args.no_translate,
                force=args.force,
            ),
        )
    )

    output_path = (
        Path(args.output)
        if args.output
        else filepath.parent / f"{filepath.stem}_anki_top{args.max_vocab}.txt"
    )
    output_path.write_text(anki_content, encoding="utf-8")

    if not args.quiet:
        logger.info("")
        logger.info("=" * 60)
        logger.info("FLASHCARD GENERATION COMPLETE (INVERSE MODE)")
        logger.info("=" * 60)
        logger.info("Learning: top %d words", args.max_vocab)
        logger.info(
            "Longest excerpt you can understand: %d words",
            excerpt_length,
        )
        logger.info('  "%s"', excerpt)
        logger.info("")
        logger.info("Rarest word in excerpt: #%d", max_rank_used)
        logger.info("Flashcards: %d", num_words)
        logger.info("Output file: %s", output_path)
        _log_anki_import_instructions(output_path)
    else:
        logger.info("%s", output_path)

    return 0


def _handle_normal_mode(
    args: argparse.Namespace,
    filepath: Path,
) -> int:
    """Handle normal mode (--length) flashcard generation.

    Args:
        args: Parsed command line arguments.
        filepath: Path to source file.

    Returns:
        Exit code.
    """
    if not args.quiet:
        logger.info("Analyzing %s...", filepath.name)
        logger.info("Finding vocabulary for %d-word excerpt...", args.length)

    anki_content, excerpt, num_words, max_rank = generate_flashcards(
        filepath,
        args.length,
        FlashcardOptions(
            source_lang=args.source_lang,
            target_lang=args.target_lang,
            deck_name=args.deck_name,
            include_context=args.include_context,
            no_translate=args.no_translate,
            force=args.force,
        ),
        all_vocab=not args.excerpt_words_only,
    )

    output_path = (
        Path(args.output)
        if args.output
        else filepath.parent / f"{filepath.stem}_anki_{args.length}.txt"
    )
    output_path.write_text(anki_content, encoding="utf-8")

    if not args.quiet:
        logger.info("")
        logger.info("=" * 60)
        logger.info("FLASHCARD GENERATION COMPLETE")
        logger.info("=" * 60)
        logger.info("Excerpt to understand (%d words):", args.length)
        logger.info('  "%s"', excerpt)
        logger.info("")
        logger.info("Max word rank needed: #%d", max_rank)
        if args.excerpt_words_only:
            logger.info("Flashcards: %d (excerpt words only)", num_words)
        else:
            logger.info(
                "Flashcards: %d (ALL words rank #1 to #%d)",
                num_words,
                max_rank,
            )
        logger.info("Output file: %s", output_path)
        _log_anki_import_instructions(output_path)
    else:
        logger.info("%s", output_path)

    return 0


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the CLI.

    Returns:
        Configured argument parser.
    """
    parser = argparse.ArgumentParser(
        description="Generate Anki flashcards from vocabulary analysis.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--file",
        "-f",
        type=str,
        default=None,
        help="Path to the text file to analyze",
    )
    parser.add_argument(
        "--length",
        "-l",
        type=int,
        default=None,
        help=("Target excerpt length (how many words you want to understand)"),
    )
    parser.add_argument(
        "--max-vocab",
        "-v",
        type=int,
        default=None,
        help=(
            "INVERSE MODE: Learn top N words, find longest excerpt you can understand"
        ),
    )
    parser.add_argument(
        "--from",
        dest="source_lang",
        type=str,
        default=None,
        help=(
            "Source language code (e.g., 'pl', 'la', 'de'). "
            "Auto-detected if not specified."
        ),
    )
    parser.add_argument(
        "--to",
        "-T",
        dest="target_lang",
        type=str,
        default="en",
        help="Target language code for translations (default: 'en')",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Output file path (default: <filename>_anki_<length>.txt)",
    )
    parser.add_argument(
        "--include-context",
        "-c",
        action="store_true",
        help="Include example context sentences in flashcards",
    )
    parser.add_argument(
        "--deck-name",
        "-d",
        type=str,
        default=None,
        help="Name for the Anki deck (default: auto-generated)",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Only output the file path, no status messages",
    )
    parser.add_argument(
        "--excerpt-words-only",
        "-e",
        action="store_true",
        help=(
            "Only include words that appear in the excerpt "
            "(default: include ALL words up to max rank)"
        ),
    )
    parser.add_argument(
        "--no-translate",
        "-n",
        action="store_true",
        help="Skip translation (output words without translations)",
    )
    parser.add_argument(
        "--force",
        "-F",
        action="store_true",
        help="Force regeneration, ignoring all caches",
    )
    parser.add_argument(
        "--cache-stats",
        action="store_true",
        help="Show cache statistics and exit",
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear all caches and exit",
    )
    return parser


def _run_generation(args: argparse.Namespace) -> int:
    """Validate args and run flashcard generation.

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code.
    """
    filepath = Path(args.file)
    if not filepath.exists():
        logger.error("Error: File not found: %s", args.file)
        return 1

    if args.max_vocab is not None:
        return _handle_inverse_mode(args, filepath)
    return _handle_normal_mode(args, filepath)


def main(argv: Sequence[str] | None = None) -> int:
    """Main entry point.

    Args:
        argv: Command line arguments.

    Returns:
        Exit code.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.cache_stats:
        return _print_cache_stats()

    if args.clear_cache:
        return _clear_caches()

    if args.file is None:
        parser.error("--file/-f is required")
    if args.length is None and args.max_vocab is None:
        parser.error("Either --length/-l or --max-vocab/-v is required")
    if args.length is not None and args.max_vocab is not None:
        parser.error("Cannot use both --length and --max-vocab. Choose one mode.")

    try:
        return _run_generation(args)
    except FileNotFoundError:
        logger.exception("File not found")
    except subprocess.CalledProcessError:
        logger.exception("Error running vocabulary_curve")
    except ValueError:
        logger.exception("Value error")
    return 1


if __name__ == "__main__":
    sys.exit(main())
