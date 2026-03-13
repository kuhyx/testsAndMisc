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
import contextlib
from dataclasses import dataclass
import logging
from pathlib import Path
import re
import subprocess
import sys
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from collections.abc import Sequence

try:
    from python_pkg.word_frequency.analyzer import read_file
    from python_pkg.word_frequency.cache import (
        AnkiDeckKey,
        clear_all_caches,
        get_all_cache_stats,
        get_anki_deck_cache,
        get_vocab_curve_cache,
    )
    from python_pkg.word_frequency.translator import (
        detect_language,
        translate_words_batch,
    )
except ImportError:
    from analyzer import read_file
    from cache import (
        AnkiDeckKey,
        clear_all_caches,
        get_all_cache_stats,
        get_anki_deck_cache,
        get_vocab_curve_cache,
    )
    from translator import detect_language, translate_words_batch

logger = logging.getLogger(__name__)

_MIN_VOCAB_DUMP_PARTS = 2
_MIN_EXCERPT_PARTS = 3
_ONE_KB = 1024
_ONE_MB = 1024 * 1024


@dataclass(frozen=True)
class FlashcardOptions:
    """Options for flashcard generation."""

    source_lang: str | None = None
    target_lang: str = "en"
    deck_name: str | None = None
    include_context: bool = False
    no_translate: bool = False
    force: bool = False


@dataclass(frozen=True)
class DeckInput:
    """Input data for Anki deck generation."""

    words_with_ranks: list[tuple[str, int]]
    source_lang: str
    target_lang: str = "en"
    contexts: dict[str, str] | None = None
    deck_name: str = "Vocabulary"


# Path to C vocabulary_curve executable
C_EXECUTABLE = (
    Path(__file__).parent.parent.parent / "C" / "vocabulary_curve" / "vocabulary_curve"
)


class VocabWord(NamedTuple):
    """A vocabulary word with its metadata."""

    word: str
    rank: int
    translation: str
    context: str


def run_vocabulary_curve(
    filepath: Path, max_length: int, *, dump_vocab: bool = False
) -> str:
    """Run the C vocabulary_curve executable.

    Args:
        filepath: Path to the text file.
        max_length: Maximum excerpt length.
        dump_vocab: If True, also dump all vocabulary up to max rank needed.

    Returns:
        Output from the executable.

    Raises:
        FileNotFoundError: If executable not found.
        subprocess.CalledProcessError: If execution fails.
    """
    if not C_EXECUTABLE.exists():
        msg = (
            f"C executable not found at {C_EXECUTABLE}. "
            "Please compile it first: cd C/vocabulary_curve && make"
        )
        raise FileNotFoundError(msg)

    cmd = [str(C_EXECUTABLE), str(filepath), str(max_length)]
    if dump_vocab:
        cmd.append("--dump-vocab")

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=120,
        check=True,
    )
    return result.stdout


def run_vocabulary_curve_inverse(
    filepath: Path, max_vocab: int, *, dump_vocab: bool = False
) -> str:
    """Run the C vocabulary_curve executable in inverse mode.

    Args:
        filepath: Path to the text file.
        max_vocab: Maximum vocabulary size (top N words).
        dump_vocab: If True, also dump all vocabulary up to max_vocab.

    Returns:
        Output from the executable.

    Raises:
        FileNotFoundError: If executable not found.
        subprocess.CalledProcessError: If execution fails.
    """
    if not C_EXECUTABLE.exists():
        msg = (
            f"C executable not found at {C_EXECUTABLE}. "
            "Please compile it first: cd C/vocabulary_curve && make"
        )
        raise FileNotFoundError(msg)

    cmd = [str(C_EXECUTABLE), str(filepath), "--max-vocab", str(max_vocab)]
    if dump_vocab:
        cmd.append("--dump-vocab")

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=120,
        check=True,
    )
    return result.stdout


def _parse_vocab_dump(lines: list[str]) -> list[tuple[str, int]]:
    """Parse VOCAB_DUMP section from output lines.

    Args:
        lines: Output lines from vocabulary_curve.

    Returns:
        List of (word, rank) tuples.
    """
    all_vocab: list[tuple[str, int]] = []
    in_vocab_dump = False
    for line in lines:
        stripped = line.strip()
        if stripped == "VOCAB_DUMP_START":
            in_vocab_dump = True
            continue
        if stripped == "VOCAB_DUMP_END":
            break
        if in_vocab_dump and ";" in stripped:
            parts = stripped.split(";")
            if len(parts) == _MIN_VOCAB_DUMP_PARTS:
                word, rank_str = parts
                with contextlib.suppress(ValueError):
                    all_vocab.append((word, int(rank_str)))
    return all_vocab


def _parse_excerpt_lines(lines: list[str], start: int) -> str:
    """Parse excerpt text from output lines starting after 'Excerpt:'.

    Args:
        lines: Output lines.
        start: Index of the line after 'Excerpt:'.

    Returns:
        Joined excerpt text.
    """
    excerpt_parts: list[str] = []
    idx = start
    while idx < len(lines):
        next_line = lines[idx].strip()
        next_line = next_line.removeprefix('"')
        if next_line.endswith('"'):
            next_line = next_line[:-1]
            excerpt_parts.append(next_line)
            break
        excerpt_parts.append(next_line)
        idx += 1
    return " ".join(excerpt_parts)


def parse_inverse_mode_output(
    output: str,
) -> tuple[str, int, int, list[tuple[str, int]]]:
    """Parse output from vocabulary_curve inverse mode.

    Args:
        output: Raw output from vocabulary_curve --max-vocab.

    Returns:
        Tuple of (excerpt_text, excerpt_length, max_rank_used, all_vocab_words).
    """
    lines = output.split("\n")
    excerpt = ""
    excerpt_length = 0
    max_rank_used = 0

    for i, raw_line in enumerate(lines):
        line = raw_line.strip()

        if line.startswith("LONGEST EXCERPT:"):
            parts = line.split()
            if len(parts) >= _MIN_EXCERPT_PARTS:
                excerpt_length = int(parts[2])

        elif line.startswith("Excerpt:"):
            excerpt = _parse_excerpt_lines(lines, i + 1)

        elif line.startswith("Rarest word used:"):
            match = re.search(r"\(#(\d+)\)", line)
            if match:
                max_rank_used = int(match.group(1))

    all_vocab = _parse_vocab_dump(lines)
    return excerpt, excerpt_length, max_rank_used, all_vocab


def _parse_target_length_block(
    lines: list[str],
    target_length: int,
) -> tuple[str, list[tuple[str, int]]]:
    """Parse the [Length N] block from vocabulary curve output.

    Args:
        lines: Output lines.
        target_length: Target excerpt length to find.

    Returns:
        Tuple of (excerpt, excerpt_words).
    """
    excerpt = ""
    excerpt_words: list[tuple[str, int]] = []
    i = 0
    while i < len(lines):
        if lines[i].strip().startswith(f"[Length {target_length}]"):
            i += 1
            # Find excerpt line
            while i < len(lines) and not lines[i].strip().startswith(
                "Excerpt:"
            ):
                i += 1
            if i < len(lines):
                excerpt_line = lines[i].strip()
                if '"' in excerpt_line:
                    start = excerpt_line.index('"') + 1
                    end = excerpt_line.rindex('"')
                    excerpt = excerpt_line[start:end]
            # Find words line
            i += 1
            while i < len(lines) and not lines[i].strip().startswith(
                "Words:"
            ):
                i += 1
            if i < len(lines):
                words_line = lines[i].strip()
                if words_line.startswith("Words:"):
                    words_part = words_line[6:].strip()
                    pattern = r"(\S+)\(#(\d+)\)"
                    matches = re.findall(pattern, words_part)
                    excerpt_words = [
                        (w, int(r)) for w, r in matches
                    ]
            break
        i += 1
    return excerpt, excerpt_words


def parse_vocabulary_curve_output(
    output: str, target_length: int
) -> tuple[str, list[tuple[str, int]], list[tuple[str, int]]]:
    """Parse output from vocabulary_curve to get words needed.

    Args:
        output: Raw output from vocabulary_curve.
        target_length: The target excerpt length.

    Returns:
        Tuple of (excerpt_text, excerpt_words, all_vocab_words).
        excerpt_words: words in the excerpt with their ranks.
        all_vocab_words: all words up to max rank
            (from VOCAB_DUMP if present).
    """
    lines = output.split("\n")

    excerpt, excerpt_words = _parse_target_length_block(
        lines, target_length
    )
    all_vocab = _parse_vocab_dump(lines)

    return excerpt, excerpt_words, all_vocab


def find_word_contexts(
    text: str,
    words: list[str],
    context_words: int = 5,
) -> dict[str, str]:
    """Find example contexts for each word in the text.

    Args:
        text: The source text.
        words: List of words to find contexts for.
        context_words: Number of words of context on each side.

    Returns:
        Dict mapping word to example context.
    """
    # Extract all words preserving positions
    all_words = re.findall(r"\b[\w]+\b", text, re.UNICODE)
    all_words_lower = [w.lower() for w in all_words]

    contexts: dict[str, str] = {}
    words_lower = {w.lower() for w in words}

    for target in words_lower:
        # Find first occurrence
        for i, word in enumerate(all_words_lower):
            if word == target:
                start = max(0, i - context_words)
                end = min(len(all_words), i + context_words + 1)
                context = " ".join(all_words[start:end])
                contexts[target] = f"...{context}..."
                break

    return contexts


def _format_excerpt_card(
    excerpt: str,
    excerpt_words: list[tuple[str, int]] | None,
) -> str:
    """Format the excerpt as the first Anki card.

    Args:
        excerpt: The target excerpt text.
        excerpt_words: Words in the excerpt with ranks.

    Returns:
        Formatted excerpt card line.
    """
    excerpt_escaped = excerpt.replace(";", ",")
    if excerpt_words:
        most_frequent = min(excerpt_words, key=lambda x: x[1])[0]
        rarest = max(excerpt_words, key=lambda x: x[1])[0]
        if most_frequent != rarest:
            pattern_rare = re.compile(
                rf"\b({re.escape(rarest)})\b", re.IGNORECASE
            )
            excerpt_escaped = pattern_rare.sub(
                r"<b>\1</b>", excerpt_escaped
            )
            pattern_freq = re.compile(
                rf"\b({re.escape(most_frequent)})\b",
                re.IGNORECASE,
            )
            excerpt_escaped = pattern_freq.sub(
                r"<i>\1</i>", excerpt_escaped
            )
        else:
            pattern = re.compile(
                rf"\b({re.escape(most_frequent)})\b",
                re.IGNORECASE,
            )
            excerpt_escaped = pattern.sub(
                r"<b><i>\1</i></b>", excerpt_escaped
            )
    return f"\U0001f4d6 TARGET EXCERPT;{excerpt_escaped};#0"


def _build_translation_lookup(
    words_with_ranks: list[tuple[str, int]],
    source_lang: str,
    target_lang: str,
    *,
    no_translate: bool = False,
) -> dict[str, str]:
    """Build word-to-translation lookup dict.

    Args:
        words_with_ranks: List of (word, rank) tuples.
        source_lang: Source language code.
        target_lang: Target language code.
        no_translate: If True, use placeholder translations.

    Returns:
        Dict mapping lowercase word to translation.
    """
    words = [w for w, _ in words_with_ranks]
    if no_translate:
        return {w.lower(): "[TODO]" for w in words}
    translations = translate_words_batch(words, source_lang, target_lang)
    trans_lookup: dict[str, str] = {}
    for result in translations:
        if result.success:
            trans_lookup[result.source_word.lower()] = (
                result.translated_word
            )
        else:
            trans_lookup[result.source_word.lower()] = (
                f"[{result.source_word}]"
            )
    return trans_lookup


def generate_anki_deck(
    deck_input: DeckInput,
    *,
    include_context: bool = False,
    no_translate: bool = False,
    excerpt: str = "",
    excerpt_words: list[tuple[str, int]] | None = None,
) -> str:
    """Generate Anki-compatible deck content.

    Args:
        deck_input: Core deck data (words, langs, contexts, name).
        include_context: Whether to include context in cards.
        no_translate: If True, skip translation (use placeholder).
        excerpt: The target excerpt text to include in cards.
        excerpt_words: Words in the excerpt with ranks.

    Returns:
        Semicolon-separated content ready for Anki import.
    """
    lines: list[str] = []

    # Add Anki headers
    lines.append("#separator:semicolon")
    lines.append("#html:true")
    lines.append(f"#deck:{deck_input.deck_name}")
    lines.append(f"#tags:vocabulary {deck_input.source_lang}")
    if include_context:
        lines.append("#columns:Front;Back;Rank;Context")
    else:
        lines.append("#columns:Front;Back;Rank")
    lines.append("")  # Empty line before data

    if excerpt:
        lines.append(_format_excerpt_card(excerpt, excerpt_words))

    trans_lookup = _build_translation_lookup(
        deck_input.words_with_ranks,
        deck_input.source_lang,
        deck_input.target_lang,
        no_translate=no_translate,
    )

    # Generate cards
    for word, rank in deck_input.words_with_ranks:
        translation = trans_lookup.get(word.lower(), f"[{word}]")

        # Escape semicolons in fields
        word_escaped = word.replace(";", ",")
        translation_escaped = translation.replace(";", ",")

        if include_context and deck_input.contexts:
            context = deck_input.contexts.get(word.lower(), "")
            if context:
                context_escaped = context.replace(";", ",")
                pattern = re.compile(re.escape(word), re.IGNORECASE)
                context_escaped = pattern.sub(
                    f"<b>{word}</b>", context_escaped
                )
            else:
                context_escaped = ""
            lines.append(
                f"{word_escaped};{translation_escaped}"
                f";#{rank};{context_escaped}"
            )
        else:
            lines.append(f"{word_escaped};{translation_escaped};#{rank}")

    return "\n".join(lines)


def get_cached_excerpt(
    filepath: Path, length: int, *, force: bool = False
) -> tuple[str, list[tuple[str, int]]] | None:
    """Get cached excerpt if available.

    Args:
        filepath: Path to source file.
        length: Excerpt length.
        force: If True, ignore cache.

    Returns:
        Tuple of (excerpt, words) or None if not cached.
    """
    if force:
        return None
    return get_vocab_curve_cache().get(filepath, length)


def cache_excerpt(
    filepath: Path, length: int, excerpt: str, words: list[tuple[str, int]]
) -> None:
    """Store excerpt in cache.

    Args:
        filepath: Path to source file.
        length: Excerpt length.
        excerpt: The excerpt text.
        words: List of (word, rank) tuples.
    """
    get_vocab_curve_cache().set(filepath, length, excerpt, words)


def get_cached_deck(
    key: AnkiDeckKey,
    *,
    force: bool = False,
) -> tuple[str, str, int, int] | None:
    """Get cached Anki deck if available.

    Args:
        key: Cache key parameters.
        force: If True, ignore cache.

    Returns:
        Tuple of (content, excerpt, num_words, max_rank) or None.
    """
    if force:
        return None
    return get_anki_deck_cache().get(key)


def cache_deck(
    key: AnkiDeckKey,
    anki_content: str,
    excerpt: str,
    num_words: int,
    max_rank: int,
) -> None:
    """Store Anki deck in cache.

    Args:
        key: Cache key parameters.
        anki_content: The deck content.
        excerpt: The excerpt text.
        num_words: Number of words.
        max_rank: Maximum rank.
    """
    get_anki_deck_cache().set(
        key,
        anki_content,
        excerpt,
        num_words,
        max_rank,
    )


def _detect_source_language(
    filepath: Path,
    text: str,
) -> str:
    """Auto-detect source language from file content.

    Args:
        filepath: Path to source file.
        text: Already-read text (may be empty).

    Returns:
        Detected language code.

    Raises:
        ValueError: If language cannot be detected.
    """
    sample_text = read_file(filepath)[:1000] if not text else text[:1000]
    detected = detect_language(sample_text)
    if detected is None:
        msg = (
            "Could not auto-detect source language. "
            "Please specify with --from (e.g., --from pl for Polish). "
            "Install langdetect for auto-detection: "
            "pip install langdetect"
        )
        raise ValueError(msg)
    return detected


def generate_flashcards(
    filepath: str | Path,
    excerpt_length: int,
    options: FlashcardOptions | None = None,
    *,
    all_vocab: bool = True,
) -> tuple[str, str, int, int]:
    """Generate Anki flashcards for vocabulary needed for an excerpt.

    Args:
        filepath: Path to the source text file.
        excerpt_length: Target excerpt length.
        options: Flashcard generation options.
        all_vocab: If True, include ALL words rank 1 to max rank.

    Returns:
        Tuple of (anki_content, excerpt, num_words, max_rank).
    """
    if options is None:
        options = FlashcardOptions()
    filepath = Path(filepath)
    deck_key = AnkiDeckKey(
        filepath=filepath,
        length=excerpt_length,
        target_lang=options.target_lang,
        include_context=options.include_context,
        all_vocab=all_vocab,
    )

    # Check for cached full deck (if not using no_translate)
    if not options.no_translate and not options.force:
        cached = get_cached_deck(deck_key)
        if cached is not None:
            return cached

    # Read the text (only needed for context finding)
    text = read_file(filepath) if options.include_context else ""

    # Auto-detect language if not provided
    source_lang = options.source_lang
    if source_lang is None:
        source_lang = _detect_source_language(filepath, text)

    # Run vocabulary curve analysis with vocab dump for all words
    output = run_vocabulary_curve(
        filepath, excerpt_length, dump_vocab=all_vocab
    )
    excerpt, excerpt_words, all_vocab_words = parse_vocabulary_curve_output(
        output, excerpt_length
    )

    if not excerpt_words:
        msg = f"No words found for excerpt length {excerpt_length}"
        raise ValueError(msg)

    max_rank = max(rank for _, rank in excerpt_words)
    words_with_ranks = (
        all_vocab_words if all_vocab and all_vocab_words else excerpt_words
    )

    contexts = None
    if options.include_context:
        if not text:
            text = read_file(filepath)
        words = [w for w, _ in words_with_ranks]
        contexts = find_word_contexts(text, words)

    deck_name = options.deck_name or f"{filepath.stem}_vocab_{excerpt_length}"

    anki_content = generate_anki_deck(
        DeckInput(
            words_with_ranks=words_with_ranks,
            source_lang=source_lang,
            target_lang=options.target_lang,
            contexts=contexts,
            deck_name=deck_name,
        ),
        include_context=options.include_context,
        no_translate=options.no_translate,
        excerpt=excerpt,
        excerpt_words=excerpt_words,
    )

    if not options.no_translate:
        cache_deck(
            deck_key,
            anki_content,
            excerpt,
            len(words_with_ranks),
            max_rank,
        )

    return anki_content, excerpt, len(words_with_ranks), max_rank


def generate_flashcards_inverse(
    filepath: str | Path,
    max_vocab: int,
    options: FlashcardOptions | None = None,
) -> tuple[str, str, int, int, int]:
    """Generate Anki flashcards for the longest excerpt using top N words.

    This is the inverse mode: given a vocabulary size, find the longest
    excerpt that can be understood with only those words.

    Args:
        filepath: Path to the source text file.
        max_vocab: Maximum vocabulary size (top N words to learn).
        options: Flashcard generation options.

    Returns:
        Tuple of (anki_content, excerpt, excerpt_length,
        num_words, max_rank_used).
    """
    if options is None:
        options = FlashcardOptions()
    filepath = Path(filepath)

    text = read_file(filepath) if options.include_context else ""

    source_lang = options.source_lang
    if source_lang is None:
        source_lang = _detect_source_language(filepath, text)

    output = run_vocabulary_curve_inverse(
        filepath, max_vocab, dump_vocab=True
    )
    excerpt, excerpt_length, max_rank_used, all_vocab_words = (
        parse_inverse_mode_output(output)
    )

    if excerpt_length == 0:
        msg = (
            f"No valid excerpt found using only top {max_vocab} "
            "words. Try increasing the vocabulary limit."
        )
        raise ValueError(msg)

    if not all_vocab_words:
        msg = f"No vocabulary returned for max_vocab={max_vocab}"
        raise ValueError(msg)

    words_with_ranks = all_vocab_words

    excerpt_word_set = set(excerpt.lower().split())
    excerpt_words = [
        (w, r)
        for w, r in all_vocab_words
        if w.lower() in excerpt_word_set
    ]

    contexts = None
    if options.include_context:
        if not text:
            text = read_file(filepath)
        words = [w for w, _ in words_with_ranks]
        contexts = find_word_contexts(text, words)

    deck_name = options.deck_name or f"{filepath.stem}_top{max_vocab}"

    anki_content = generate_anki_deck(
        DeckInput(
            words_with_ranks=words_with_ranks,
            source_lang=source_lang,
            target_lang=options.target_lang,
            contexts=contexts,
            deck_name=deck_name,
        ),
        include_context=options.include_context,
        no_translate=options.no_translate,
        excerpt=excerpt,
        excerpt_words=excerpt_words or None,
    )

    return (
        anki_content,
        excerpt,
        excerpt_length,
        len(words_with_ranks),
        max_rank_used,
    )


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
        else filepath.parent
        / f"{filepath.stem}_anki_top{args.max_vocab}.txt"
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
        logger.info(
            "Finding vocabulary for %d-word excerpt...", args.length
        )

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
        logger.info(
            "Excerpt to understand (%d words):", args.length
        )
        logger.info('  "%s"', excerpt)
        logger.info("")
        logger.info("Max word rank needed: #%d", max_rank)
        if args.excerpt_words_only:
            logger.info(
                "Flashcards: %d (excerpt words only)", num_words
            )
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
        help=(
            "Target excerpt length "
            "(how many words you want to understand)"
        ),
    )
    parser.add_argument(
        "--max-vocab",
        "-v",
        type=int,
        default=None,
        help=(
            "INVERSE MODE: Learn top N words, "
            "find longest excerpt you can understand"
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
        parser.error(
            "Cannot use both --length and --max-vocab. Choose one mode."
        )

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
