"""Core flashcard generation logic."""

from __future__ import annotations

from pathlib import Path
import subprocess

from python_pkg.word_frequency._deck_builder import (
    find_word_contexts,
    generate_anki_deck,
)
from python_pkg.word_frequency._parsing import (
    parse_inverse_mode_output,
    parse_vocabulary_curve_output,
)
from python_pkg.word_frequency._types import (
    C_EXECUTABLE,
    DeckInput,
    FlashcardOptions,
)
from python_pkg.word_frequency.analyzer import read_file
from python_pkg.word_frequency.cache import (
    AnkiDeckKey,
    get_anki_deck_cache,
    get_vocab_curve_cache,
)
from python_pkg.word_frequency.translator import detect_language


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
