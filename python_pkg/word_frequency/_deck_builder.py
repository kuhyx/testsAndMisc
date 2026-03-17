"""Anki deck building and card formatting."""

from __future__ import annotations

import re

from python_pkg.word_frequency._types import DeckInput
from python_pkg.word_frequency.translator import translate_words_batch


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
