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
    from python_pkg.word_frequency.analyzer import read_file, analyze_text
except ImportError:
    from translator import detect_language, translate_words_batch
    from analyzer import read_file, analyze_text


# Path to C vocabulary_curve executable
C_EXECUTABLE = Path(__file__).parent.parent.parent / "C" / "vocabulary_curve" / "vocabulary_curve"


class VocabWord(NamedTuple):
    """A vocabulary word with its metadata."""

    word: str
    rank: int
    translation: str
    context: str


def run_vocabulary_curve(filepath: Path, max_length: int) -> str:
    """Run the C vocabulary_curve executable.

    Args:
        filepath: Path to the text file.
        max_length: Maximum excerpt length.

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

    result = subprocess.run(
        [str(C_EXECUTABLE), str(filepath), str(max_length)],
        capture_output=True,
        text=True,
        timeout=120,
        check=True,
    )
    return result.stdout


def parse_vocabulary_curve_output(output: str, target_length: int) -> tuple[str, list[tuple[str, int]]]:
    """Parse output from vocabulary_curve to get words needed.

    Args:
        output: Raw output from vocabulary_curve.
        target_length: The target excerpt length.

    Returns:
        Tuple of (excerpt_text, list of (word, rank) tuples).
    """
    lines = output.split("\n")
    excerpt = ""
    words: list[tuple[str, int]] = []

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
                    words = [(w, int(r)) for w, r in matches]
            break
        i += 1

    return excerpt, words


def get_top_n_words(text: str, n: int) -> list[tuple[str, int]]:
    """Get the top N most frequent words from text.

    Args:
        text: The source text.
        n: Number of top words to return.

    Returns:
        List of (word, rank) tuples, ranked 1 to n.
    """
    word_counts = analyze_text(text)
    sorted_words = sorted(word_counts.items(), key=lambda x: (-x[1], x[0]))
    return [(word, rank + 1) for rank, (word, _) in enumerate(sorted_words[:n])]


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


def generate_flashcards(
    filepath: str | Path,
    excerpt_length: int,
    source_lang: str | None = None,
    target_lang: str = "en",
    include_context: bool = False,
    deck_name: str | None = None,
    all_vocab: bool = True,
    no_translate: bool = False,
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

    Returns:
        Tuple of (anki_content, excerpt, num_words, max_rank).
    """
    filepath = Path(filepath)

    # Read the text
    text = read_file(filepath)

    # Auto-detect language if not provided
    if source_lang is None:
        source_lang = detect_language(text)
        if source_lang is None:
            source_lang = "auto"

    # Run vocabulary curve analysis
    output = run_vocabulary_curve(filepath, excerpt_length)

    # Parse the output
    excerpt, excerpt_words = parse_vocabulary_curve_output(output, excerpt_length)

    if not excerpt_words:
        raise ValueError(f"No words found for excerpt length {excerpt_length}")

    # Find max rank needed
    max_rank = max(rank for _, rank in excerpt_words)

    # Get ALL words up to max_rank if requested
    if all_vocab:
        words_with_ranks = get_top_n_words(text, max_rank)
    else:
        words_with_ranks = excerpt_words

    # Get contexts if requested
    contexts = None
    if include_context:
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
    )

    return anki_content, excerpt, len(words_with_ranks), max_rank


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
        required=True,
        help="Path to the text file to analyze",
    )
    parser.add_argument(
        "--length",
        "-l",
        type=int,
        required=True,
        help="Target excerpt length (how many words you want to understand)",
    )
    parser.add_argument(
        "--from",
        "-F",
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

    args = parser.parse_args(argv)

    try:
        filepath = Path(args.file)
        if not filepath.exists():
            print(f"Error: File not found: {args.file}", file=sys.stderr)  # noqa: T201
            return 1

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
