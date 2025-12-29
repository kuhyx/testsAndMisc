#!/usr/bin/env python3
"""Anki flashcard generator from vocabulary curve analysis.

Generates Anki-compatible flashcard decks from the vocabulary needed to
understand excerpts of a given length.

Usage:
    # Generate flashcards for a 20-word excerpt
    python -m python_pkg.word_frequency.anki_generator --file text.txt --length 20

    # Specify source language (auto-detected by default)
    python -m python_pkg.word_frequency.anki_generator --file text.txt --length 20 --from pl

    # Custom output file
    python -m python_pkg.word_frequency.anki_generator --file text.txt --length 20 --output polish_vocab.txt

    # Include example sentences/context
    python -m python_pkg.word_frequency.anki_generator --file text.txt --length 20 --include-context

Output:
    Creates a semicolon-separated text file that can be imported into Anki.
    Format: word;translation;frequency_rank;example_context (optional)
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from collections.abc import Sequence

try:
    from python_pkg.word_frequency.translator import (
        detect_language,
        translate_words_batch,
    )
    from python_pkg.word_frequency.analyzer import read_file
except ImportError:
    from translator import detect_language, translate_words_batch
    from analyzer import read_file


# Path to C vocabulary_curve executable
C_EXECUTABLE = Path(__file__).parent.parent.parent / "C" / "vocabulary_curve" / "vocabulary_curve"


class VocabWord(NamedTuple):
    """A vocabulary word with its metadata."""

    word: str
    rank: int
    translation: str
    context: str


def run_vocabulary_curve(filepath: Path, max_length: int, *, dump_vocab: bool = False) -> str:
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
        raise FileNotFoundError(
            f"C executable not found at {C_EXECUTABLE}. "
            "Please compile it first: cd C/vocabulary_curve && make"
        )

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


def run_vocabulary_curve_inverse(filepath: Path, max_vocab: int, *, dump_vocab: bool = False) -> str:
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
        raise FileNotFoundError(
            f"C executable not found at {C_EXECUTABLE}. "
            "Please compile it first: cd C/vocabulary_curve && make"
        )

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


def parse_inverse_mode_output(output: str) -> tuple[str, int, int, list[tuple[str, int]]]:
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
    all_vocab: list[tuple[str, int]] = []

    for i, line in enumerate(lines):
        line = line.strip()
        
        if line.startswith("LONGEST EXCERPT:"):
            parts = line.split()
            if len(parts) >= 3:
                excerpt_length = int(parts[2])
        
        elif line.startswith("Excerpt:"):
            # Next line(s) contain the excerpt
            i += 1
            excerpt_parts = []
            while i < len(lines):
                next_line = lines[i].strip()
                if next_line.startswith('"'):
                    next_line = next_line[1:]
                if next_line.endswith('"'):
                    next_line = next_line[:-1]
                    excerpt_parts.append(next_line)
                    break
                excerpt_parts.append(next_line)
                i += 1
            excerpt = " ".join(excerpt_parts)
        
        elif line.startswith("Rarest word used:"):
            # Parse "word (#rank)"
            match = re.search(r"\(#(\d+)\)", line)
            if match:
                max_rank_used = int(match.group(1))

    # Parse VOCAB_DUMP section if present
    in_vocab_dump = False
    for line in lines:
        if line.strip() == "VOCAB_DUMP_START":
            in_vocab_dump = True
            continue
        if line.strip() == "VOCAB_DUMP_END":
            break
        if in_vocab_dump and ";" in line:
            parts = line.strip().split(";")
            if len(parts) == 2:
                word, rank_str = parts
                try:
                    all_vocab.append((word, int(rank_str)))
                except ValueError:
                    pass

    return excerpt, excerpt_length, max_rank_used, all_vocab


def parse_vocabulary_curve_output(output: str, target_length: int) -> tuple[str, list[tuple[str, int]], list[tuple[str, int]]]:
    """Parse output from vocabulary_curve to get words needed.

    Args:
        output: Raw output from vocabulary_curve.
        target_length: The target excerpt length.

    Returns:
        Tuple of (excerpt_text, excerpt_words, all_vocab_words).
        excerpt_words: words in the excerpt with their ranks.
        all_vocab_words: all words up to max rank (from VOCAB_DUMP if present).
    """
    lines = output.split("\n")
    excerpt = ""
    excerpt_words: list[tuple[str, int]] = []
    all_vocab: list[tuple[str, int]] = []

    # Find the line for the target length
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith(f"[Length {target_length}]"):
            # Found our target length, now get excerpt and words
            i += 1
            # Find excerpt line
            while i < len(lines) and not lines[i].strip().startswith("Excerpt:"):
                i += 1
            if i < len(lines):
                excerpt_line = lines[i].strip()
                if '"' in excerpt_line:
                    start = excerpt_line.index('"') + 1
                    end = excerpt_line.rindex('"')
                    excerpt = excerpt_line[start:end]

            # Find words line
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("Words:"):
                i += 1
            if i < len(lines):
                words_line = lines[i].strip()
                if words_line.startswith("Words:"):
                    words_part = words_line[6:].strip()
                    # Parse "word(#rank), word2(#rank2), ..."
                    pattern = r"(\S+)\(#(\d+)\)"
                    matches = re.findall(pattern, words_part)
                    excerpt_words = [(w, int(r)) for w, r in matches]
            break
        i += 1

    # Parse VOCAB_DUMP section if present
    in_vocab_dump = False
    for line in lines:
        if line.strip() == "VOCAB_DUMP_START":
            in_vocab_dump = True
            continue
        if line.strip() == "VOCAB_DUMP_END":
            break
        if in_vocab_dump and ";" in line:
            parts = line.strip().split(";")
            if len(parts) == 2:
                word, rank_str = parts
                try:
                    all_vocab.append((word, int(rank_str)))
                except ValueError:
                    pass

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


def generate_anki_deck(
    words_with_ranks: list[tuple[str, int]],
    source_lang: str,
    target_lang: str = "en",
    contexts: dict[str, str] | None = None,
    deck_name: str = "Vocabulary",
    include_context: bool = False,
    no_translate: bool = False,
    excerpt: str = "",
    excerpt_words: list[tuple[str, int]] | None = None,
) -> str:
    """Generate Anki-compatible deck content.

    Args:
        words_with_ranks: List of (word, rank) tuples.
        source_lang: Source language code.
        target_lang: Target language code (default: en).
        contexts: Optional dict of word -> context.
        deck_name: Name for the deck.
        include_context: Whether to include context in cards.
        no_translate: If True, skip translation (use placeholder).
        excerpt: The target excerpt text to include in cards.
        excerpt_words: List of (word, rank) tuples for words in the excerpt.

    Returns:
        Semicolon-separated content ready for Anki import.
    """
    lines: list[str] = []

    # Add Anki headers
    lines.append(f"#separator:semicolon")
    lines.append(f"#html:true")
    lines.append(f"#deck:{deck_name}")
    lines.append(f"#tags:vocabulary {source_lang}")
    if include_context:
        lines.append("#columns:Front;Back;Rank;Context")
    else:
        lines.append("#columns:Front;Back;Rank")
    lines.append("")  # Empty line before data

    # Add excerpt as first card (goal/context card)
    if excerpt:
        excerpt_escaped = excerpt.replace(";", ",")
        # Use excerpt_words from C output (has correct ranks)
        if excerpt_words:
            # Most frequent = lowest rank (italics), rarest = highest rank (bold)
            most_frequent = min(excerpt_words, key=lambda x: x[1])[0]
            rarest = max(excerpt_words, key=lambda x: x[1])[0]
            # Apply formatting - rarest first (bold), then most frequent (italics)
            # to avoid nested tag issues if they're the same word
            if most_frequent != rarest:
                pattern_rare = re.compile(rf"\b({re.escape(rarest)})\b", re.IGNORECASE)
                excerpt_escaped = pattern_rare.sub(r"<b>\1</b>", excerpt_escaped)
                pattern_freq = re.compile(rf"\b({re.escape(most_frequent)})\b", re.IGNORECASE)
                excerpt_escaped = pattern_freq.sub(r"<i>\1</i>", excerpt_escaped)
            else:
                # Same word is both most and least frequent - use bold+italic
                pattern = re.compile(rf"\b({re.escape(most_frequent)})\b", re.IGNORECASE)
                excerpt_escaped = pattern.sub(r"<b><i>\1</i></b>", excerpt_escaped)
        lines.append(f"📖 TARGET EXCERPT;{excerpt_escaped};#0")

    # Get translations (or skip if no_translate)
    words = [w for w, _ in words_with_ranks]
    if no_translate:
        trans_lookup = {w.lower(): "[TODO]" for w in words}
    else:
        translations = translate_words_batch(words, source_lang, target_lang)
        # Build translation lookup
        trans_lookup = {}
        for result in translations:
            if result.success:
                trans_lookup[result.source_word.lower()] = result.translated_word
            else:
                trans_lookup[result.source_word.lower()] = f"[{result.source_word}]"

    # Generate cards
    for word, rank in words_with_ranks:
        translation = trans_lookup.get(word.lower(), f"[{word}]")

        # Escape semicolons in fields
        word_escaped = word.replace(";", ",")
        translation_escaped = translation.replace(";", ",")

        if include_context and contexts:
            context = contexts.get(word.lower(), "")
            # Highlight the word in context
            if context:
                context_escaped = context.replace(";", ",")
                # Make target word bold in context
                pattern = re.compile(re.escape(word), re.IGNORECASE)
                context_escaped = pattern.sub(f"<b>{word}</b>", context_escaped)
            else:
                context_escaped = ""
            lines.append(f"{word_escaped};{translation_escaped};#{rank};{context_escaped}")
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
    try:
        from python_pkg.word_frequency.cache import get_vocab_curve_cache
        return get_vocab_curve_cache().get(filepath, length)
    except ImportError:
        return None


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
    try:
        from python_pkg.word_frequency.cache import get_vocab_curve_cache
        get_vocab_curve_cache().set(filepath, length, excerpt, words)
    except ImportError:
        pass


def get_cached_deck(
    filepath: Path,
    length: int,
    target_lang: str,
    include_context: bool,
    all_vocab: bool,
    *,
    force: bool = False,
) -> tuple[str, str, int, int] | None:
    """Get cached Anki deck if available.

    Args:
        filepath: Path to source file.
        length: Excerpt length.
        target_lang: Target language.
        include_context: Whether context is included.
        all_vocab: Whether all vocab is included.
        force: If True, ignore cache.

    Returns:
        Tuple of (content, excerpt, num_words, max_rank) or None.
    """
    if force:
        return None
    try:
        from python_pkg.word_frequency.cache import get_anki_deck_cache
        return get_anki_deck_cache().get(
            filepath, length, target_lang, include_context, all_vocab
        )
    except ImportError:
        return None


def cache_deck(
    filepath: Path,
    length: int,
    target_lang: str,
    include_context: bool,
    all_vocab: bool,
    anki_content: str,
    excerpt: str,
    num_words: int,
    max_rank: int,
) -> None:
    """Store Anki deck in cache.

    Args:
        filepath: Path to source file.
        length: Excerpt length.
        target_lang: Target language.
        include_context: Whether context is included.
        all_vocab: Whether all vocab is included.
        anki_content: The deck content.
        excerpt: The excerpt text.
        num_words: Number of words.
        max_rank: Maximum rank.
    """
    try:
        from python_pkg.word_frequency.cache import get_anki_deck_cache
        get_anki_deck_cache().set(
            filepath,
            length,
            target_lang,
            include_context,
            all_vocab,
            anki_content,
            excerpt,
            num_words,
            max_rank,
        )
    except ImportError:
        pass


def generate_flashcards(
    filepath: str | Path,
    excerpt_length: int,
    source_lang: str | None = None,
    target_lang: str = "en",
    include_context: bool = False,
    deck_name: str | None = None,
    all_vocab: bool = True,
    no_translate: bool = False,
    *,
    force: bool = False,
) -> tuple[str, str, int, int]:
    """Generate Anki flashcards for vocabulary needed for an excerpt length.

    Args:
        filepath: Path to the source text file.
        excerpt_length: Target excerpt length.
        source_lang: Source language (auto-detected if None).
        target_lang: Target language for translations.
        include_context: Whether to include example contexts.
        deck_name: Optional deck name.
        all_vocab: If True, include ALL words from rank 1 to max rank needed.
                   If False, only include words that appear in the excerpt.
        no_translate: If True, skip translation.
        force: If True, ignore all caches and regenerate.

    Returns:
        Tuple of (anki_content, excerpt, num_words, max_rank).
    """
    filepath = Path(filepath)

    # Check for cached full deck (if not using no_translate)
    if not no_translate and not force:
        cached = get_cached_deck(
            filepath, excerpt_length, target_lang, include_context, all_vocab
        )
        if cached is not None:
            return cached

    # Read the text (only needed for context finding)
    text = read_file(filepath) if include_context else ""

    # Auto-detect language if not provided
    if source_lang is None:
        sample_text = read_file(filepath)[:1000] if not text else text[:1000]
        source_lang = detect_language(sample_text)
        if source_lang is None:
            raise ValueError(
                "Could not auto-detect source language. "
                "Please specify with --from (e.g., --from pl for Polish). "
                "Install langdetect for auto-detection: pip install langdetect"
            )

    # Run vocabulary curve analysis with vocab dump for all words
    output = run_vocabulary_curve(filepath, excerpt_length, dump_vocab=all_vocab)
    # Parse the output (now includes all vocabulary from C)
    excerpt, excerpt_words, all_vocab_words = parse_vocabulary_curve_output(output, excerpt_length)

    if not excerpt_words:
        raise ValueError(f"No words found for excerpt length {excerpt_length}")

    # Find max rank needed
    max_rank = max(rank for _, rank in excerpt_words)

    # Use vocabulary from C output
    if all_vocab and all_vocab_words:
        words_with_ranks = all_vocab_words
    else:
        words_with_ranks = excerpt_words

    # Get contexts if requested
    contexts = None
    if include_context:
        if not text:
            text = read_file(filepath)
        words = [w for w, _ in words_with_ranks]
        contexts = find_word_contexts(text, words)

    # Generate deck name
    if deck_name is None:
        deck_name = f"{filepath.stem}_vocab_{excerpt_length}"

    # Generate Anki content
    anki_content = generate_anki_deck(
        words_with_ranks,
        source_lang,
        target_lang,
        contexts,
        deck_name,
        include_context,
        no_translate,
        excerpt,
        excerpt_words,
    )

    # Cache the full deck (if translated)
    if not no_translate:
        cache_deck(
            filepath,
            excerpt_length,
            target_lang,
            include_context,
            all_vocab,
            anki_content,
            excerpt,
            len(words_with_ranks),
            max_rank,
        )

    return anki_content, excerpt, len(words_with_ranks), max_rank


def generate_flashcards_inverse(
    filepath: str | Path,
    max_vocab: int,
    source_lang: str | None = None,
    target_lang: str = "en",
    include_context: bool = False,
    deck_name: str | None = None,
    no_translate: bool = False,
    *,
    force: bool = False,
) -> tuple[str, str, int, int, int]:
    """Generate Anki flashcards for the longest excerpt using top N words.

    This is the inverse mode: given a vocabulary size, find the longest
    excerpt that can be understood with only those words.

    Args:
        filepath: Path to the source text file.
        max_vocab: Maximum vocabulary size (top N words to learn).
        source_lang: Source language (auto-detected if None).
        target_lang: Target language for translations.
        include_context: Whether to include example contexts.
        deck_name: Optional deck name.
        no_translate: If True, skip translation.
        force: If True, ignore all caches and regenerate.

    Returns:
        Tuple of (anki_content, excerpt, excerpt_length, num_words, max_rank_used).
    """
    filepath = Path(filepath)

    # Read the text (only needed for context finding)
    text = read_file(filepath) if include_context else ""

    # Auto-detect language if not provided
    if source_lang is None:
        sample_text = read_file(filepath)[:1000] if not text else text[:1000]
        source_lang = detect_language(sample_text)
        if source_lang is None:
            raise ValueError(
                "Could not auto-detect source language. "
                "Please specify with --from (e.g., --from pl for Polish). "
                "Install langdetect for auto-detection: pip install langdetect"
            )

    # Run vocabulary curve in inverse mode
    output = run_vocabulary_curve_inverse(filepath, max_vocab, dump_vocab=True)
    
    # Parse the output
    excerpt, excerpt_length, max_rank_used, all_vocab_words = parse_inverse_mode_output(output)

    if excerpt_length == 0:
        raise ValueError(
            f"No valid excerpt found using only top {max_vocab} words. "
            "Try increasing the vocabulary limit."
        )

    if not all_vocab_words:
        raise ValueError(f"No vocabulary returned for max_vocab={max_vocab}")

    # Use all vocabulary up to max_vocab
    words_with_ranks = all_vocab_words
    
    # Find words that appear in the excerpt (for highlighting)
    excerpt_word_set = set(excerpt.lower().split())
    excerpt_words = [(w, r) for w, r in all_vocab_words if w.lower() in excerpt_word_set]

    # Get contexts if requested
    contexts = None
    if include_context:
        if not text:
            text = read_file(filepath)
        words = [w for w, _ in words_with_ranks]
        contexts = find_word_contexts(text, words)

    # Generate deck name
    if deck_name is None:
        deck_name = f"{filepath.stem}_top{max_vocab}"

    # Generate Anki content
    anki_content = generate_anki_deck(
        words_with_ranks,
        source_lang,
        target_lang,
        contexts,
        deck_name,
        include_context,
        no_translate,
        excerpt,
        excerpt_words if excerpt_words else None,
    )

    return anki_content, excerpt, excerpt_length, len(words_with_ranks), max_rank_used


def main(argv: Sequence[str] | None = None) -> int:
    """Main entry point.

    Args:
        argv: Command line arguments.

    Returns:
        Exit code.
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
        help="Target excerpt length (how many words you want to understand)",
    )
    parser.add_argument(
        "--max-vocab",
        "-v",
        type=int,
        default=None,
        help="INVERSE MODE: Learn top N words, find longest excerpt you can understand",
    )
    parser.add_argument(
        "--from",
        dest="source_lang",
        type=str,
        default=None,
        help="Source language code (e.g., 'pl', 'la', 'de'). Auto-detected if not specified.",
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
        help="Only include words that appear in the excerpt (default: include ALL words up to max rank)",
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

    args = parser.parse_args(argv)

    # Handle cache management commands
    if args.cache_stats:
        try:
            from python_pkg.word_frequency.cache import get_all_cache_stats
        except ImportError:
            try:
                from cache import get_all_cache_stats
            except ImportError:
                print("Cache module not available", file=sys.stderr)  # noqa: T201
                return 1
        stats = get_all_cache_stats()
        print("Cache Statistics")  # noqa: T201
        print("=" * 50)  # noqa: T201
        for cache_name, cache_stats in stats.items():
            print(f"\n{cache_name.upper()}:")  # noqa: T201
            for key, value in cache_stats.items():
                if key == "cache_size_bytes":
                    if value < 1024:
                        size_str = f"{value} B"
                    elif value < 1024 * 1024:
                        size_str = f"{value / 1024:.1f} KB"
                    else:
                        size_str = f"{value / (1024 * 1024):.1f} MB"
                    print(f"  {key}: {size_str}")  # noqa: T201
                else:
                    print(f"  {key}: {value}")  # noqa: T201
        return 0

    if args.clear_cache:
        try:
            from python_pkg.word_frequency.cache import clear_all_caches
        except ImportError:
            try:
                from cache import clear_all_caches
            except ImportError:
                print("Cache module not available", file=sys.stderr)  # noqa: T201
                return 1
        clear_all_caches()
        print("All caches cleared.")  # noqa: T201
        return 0

    # Validate required arguments for main functionality
    if args.file is None:
        parser.error("--file/-f is required")
    if args.length is None and args.max_vocab is None:
        parser.error("Either --length/-l or --max-vocab/-v is required")
    if args.length is not None and args.max_vocab is not None:
        parser.error("Cannot use both --length and --max-vocab. Choose one mode.")

    try:
        filepath = Path(args.file)
        if not filepath.exists():
            print(f"Error: File not found: {args.file}", file=sys.stderr)  # noqa: T201
            return 1

        # INVERSE MODE: --max-vocab
        if args.max_vocab is not None:
            if not args.quiet:
                print(f"Analyzing {filepath.name}...")  # noqa: T201
                print(f"Finding longest excerpt using top {args.max_vocab} words...")  # noqa: T201

            # Generate flashcards in inverse mode
            anki_content, excerpt, excerpt_length, num_words, max_rank_used = generate_flashcards_inverse(
                filepath,
                args.max_vocab,
                source_lang=args.source_lang,
                target_lang=args.target_lang,
                include_context=args.include_context,
                deck_name=args.deck_name,
                no_translate=args.no_translate,
                force=args.force,
            )

            # Determine output path
            if args.output:
                output_path = Path(args.output)
            else:
                output_path = filepath.parent / f"{filepath.stem}_anki_top{args.max_vocab}.txt"

            # Write output
            output_path.write_text(anki_content, encoding="utf-8")

            if not args.quiet:
                print("")  # noqa: T201
                print("=" * 60)  # noqa: T201
                print("FLASHCARD GENERATION COMPLETE (INVERSE MODE)")  # noqa: T201
                print("=" * 60)  # noqa: T201
                print(f"Learning: top {args.max_vocab} words")  # noqa: T201
                print(f"Longest excerpt you can understand: {excerpt_length} words")  # noqa: T201
                print(f'  "{excerpt}"')  # noqa: T201
                print("")  # noqa: T201
                print(f"Rarest word in excerpt: #{max_rank_used}")  # noqa: T201
                print(f"Flashcards: {num_words}")  # noqa: T201
                print(f"Output file: {output_path}")  # noqa: T201
                print("")  # noqa: T201
                print("To import into Anki:")  # noqa: T201
                print("  1. Open Anki")  # noqa: T201
                print("  2. File -> Import")  # noqa: T201
                print(f"  3. Select: {output_path}")  # noqa: T201
                print("  4. Click Import")  # noqa: T201
            else:
                print(output_path)  # noqa: T201

            return 0

        # NORMAL MODE: --length
        if not args.quiet:
            print(f"Analyzing {filepath.name}...")  # noqa: T201
            print(f"Finding vocabulary for {args.length}-word excerpt...")  # noqa: T201

        # Generate flashcards
        anki_content, excerpt, num_words, max_rank = generate_flashcards(
            filepath,
            args.length,
            source_lang=args.source_lang,
            target_lang=args.target_lang,
            include_context=args.include_context,
            deck_name=args.deck_name,
            all_vocab=not args.excerpt_words_only,
            no_translate=args.no_translate,
            force=args.force,
        )

        # Determine output path
        if args.output:
            output_path = Path(args.output)
        else:
            output_path = filepath.parent / f"{filepath.stem}_anki_{args.length}.txt"

        # Write output
        output_path.write_text(anki_content, encoding="utf-8")

        if not args.quiet:
            print("")  # noqa: T201
            print("=" * 60)  # noqa: T201
            print("FLASHCARD GENERATION COMPLETE")  # noqa: T201
            print("=" * 60)  # noqa: T201
            print(f"Excerpt to understand ({args.length} words):")  # noqa: T201
            print(f'  "{excerpt}"')  # noqa: T201
            print("")  # noqa: T201
            print(f"Max word rank needed: #{max_rank}")  # noqa: T201
            if args.excerpt_words_only:
                print(f"Flashcards: {num_words} (excerpt words only)")  # noqa: T201
            else:
                print(f"Flashcards: {num_words} (ALL words rank #1 to #{max_rank})")  # noqa: T201
            print(f"Output file: {output_path}")  # noqa: T201
            print("")  # noqa: T201
            print("To import into Anki:")  # noqa: T201
            print("  1. Open Anki")  # noqa: T201
            print("  2. File -> Import")  # noqa: T201
            print(f"  3. Select: {output_path}")  # noqa: T201
            print("  4. Click Import")  # noqa: T201
        else:
            print(output_path)  # noqa: T201

        return 0

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)  # noqa: T201
        return 1
    except subprocess.CalledProcessError as e:
        print(f"Error running vocabulary_curve: {e}", file=sys.stderr)  # noqa: T201
        return 1
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)  # noqa: T201
        return 1


if __name__ == "__main__":
    sys.exit(main())
