#!/usr/bin/env python3
r"""Translator - translates words/text between languages.

This module provides translation capabilities using Argos Translate (offline).

Usage::

    python -m python_pkg.word_frequency.translator \
        --text "hello" --from en --to es

Dependencies::

    pip install argostranslate
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

try:
    import argostranslate.package
    import argostranslate.translate
except ImportError:
    argostranslate = None

try:
    from python_pkg.word_frequency.cache import (
        get_translation_cache,
    )
except ImportError:
    get_translation_cache = None

from python_pkg.word_frequency._translator_cli import main
from python_pkg.word_frequency._translator_helpers import (
    TranslationResult,
    _check_cuda_available,
    _ensure_argos_installed,
    _ensure_language_pair,
    _init_gpu_if_available,
    detect_language,
    format_translations,
    read_file,
)

__all__ = [
    "TranslationResult",
    "detect_language",
    "download_languages",
    "format_translations",
    "get_available_packages",
    "get_installed_languages",
    "main",
    "read_file",
    "translate_word",
    "translate_words",
    "translate_words_batch",
]

logger = logging.getLogger(__name__)

_BATCH_SIZE = 100


def _check_argos() -> bool:
    """Check if argostranslate is available."""
    return argostranslate is not None


def get_installed_languages() -> list[tuple[str, str]]:
    """Get list of installed languages.

    Returns:
        List of (code, name) tuples for installed languages.
    """
    if not _check_argos():
        return []

    languages = argostranslate.translate.get_installed_languages()
    return [(lang.code, lang.name) for lang in languages]


def get_available_packages() -> list[tuple[str, str, str, str]]:
    """Get list of available language packages for download.

    Returns:
        List of (from_code, from_name, to_code, to_name) tuples.
    """
    if not _check_argos():
        return []

    argostranslate.package.update_package_index()
    available = argostranslate.package.get_available_packages()
    return [
        (pkg.from_code, pkg.from_name, pkg.to_code, pkg.to_name) for pkg in available
    ]


def download_languages(lang_codes: Sequence[str]) -> dict[str, bool]:
    """Download language packages for the specified languages.

    Downloads packages for translation between English and the specified languages,
    and between each pair of specified languages if available.

    Args:
        lang_codes: List of language codes to download (e.g., ['en', 'es', 'pl']).

    Returns:
        Dict mapping "from->to" to success boolean.
    """
    if not _check_argos():
        return {}

    results: dict[str, bool] = {}

    # Update package index
    logger.info("Updating package index...")
    argostranslate.package.update_package_index()
    available = argostranslate.package.get_available_packages()

    # Create a lookup for available packages
    available_lookup: dict[tuple[str, str], object] = {}
    for pkg in available:
        available_lookup[(pkg.from_code, pkg.to_code)] = pkg

    # Download packages for all requested language pairs
    lang_codes_set = set(lang_codes)

    for from_code in lang_codes_set:
        for to_code in lang_codes_set:
            if from_code == to_code:
                continue

            key = f"{from_code}->{to_code}"
            pkg_key = (from_code, to_code)

            if pkg_key in available_lookup:
                pkg = available_lookup[pkg_key]
                try:
                    logger.info(
                        "Downloading %s -> %s...",
                        from_code,
                        to_code,
                    )
                    argostranslate.package.install_from_path(pkg.download())
                    results[key] = True
                    logger.info(
                        "  Installed %s -> %s",
                        from_code,
                        to_code,
                    )
                except (OSError, RuntimeError, ValueError) as e:
                    results[key] = False
                    logger.info(
                        "  Failed %s -> %s: %s",
                        from_code,
                        to_code,
                        e,
                    )
            else:
                # Package not available
                results[key] = False

    return results


def translate_word(
    word: str,
    from_lang: str,
    to_lang: str,
    *,
    use_cache: bool = True,
) -> TranslationResult:
    """Translate a single word using argostranslate (offline).

    Args:
        word: The word to translate.
        from_lang: Source language code (e.g., 'en', 'pl', 'la').
        to_lang: Target language code.
        use_cache: Whether to use/update translation cache.

    Returns:
        TranslationResult with the translation.

    Raises:
        ImportError: If argostranslate is not available and cannot be installed.
    """
    # Check cache first
    if use_cache and get_translation_cache is not None:
        cache = get_translation_cache()
        cached = cache.get(word, from_lang, to_lang)
        if cached is not None:
            return TranslationResult(
                source_word=word,
                translated_word=cached,
                source_lang=from_lang,
                target_lang=to_lang,
                success=True,
            )

    # Ensure argos is installed (will raise if it can't be)
    _ensure_argos_installed()

    try:
        translated = argostranslate.translate.translate(
            word,
            from_lang,
            to_lang,
        )
        # Cache the result
        if use_cache and get_translation_cache is not None:
            get_translation_cache().set(
                word,
                from_lang,
                to_lang,
                translated,
            )
        return TranslationResult(
            source_word=word,
            translated_word=translated,
            source_lang=from_lang,
            target_lang=to_lang,
            success=True,
        )
    except (OSError, RuntimeError, ValueError, TypeError) as e:
        return TranslationResult(
            source_word=word,
            translated_word="",
            source_lang=from_lang,
            target_lang=to_lang,
            success=False,
            error=str(e),
        )


def translate_words(
    words: Sequence[str],
    from_lang: str,
    to_lang: str,
    *,
    use_cache: bool = True,
) -> list[TranslationResult]:
    """Translate multiple words.

    Args:
        words: List of words to translate.
        from_lang: Source language code.
        to_lang: Target language code.
        use_cache: Whether to use translation cache.

    Returns:
        List of TranslationResult for each word.
    """
    return [
        translate_word(word, from_lang, to_lang, use_cache=use_cache) for word in words
    ]


def _translate_batch_worker(
    batch_words: list[str],
    from_lang: str,
    to_lang: str,
    batch_idx: int,
) -> tuple[int, dict[str, str]]:
    """Worker function to translate a batch of words.

    Args:
        batch_words: Words to translate in this batch.
        from_lang: Source language code.
        to_lang: Target language code.
        batch_idx: Index of this batch (for ordering results).

    Returns:
        Tuple of (batch_idx, translations dict).
    """
    translations: dict[str, str] = {}

    # Batch translate by joining with newlines
    batch_text = "\n".join(batch_words)
    translated_batch = argostranslate.translate.translate(
        batch_text, from_lang, to_lang
    )
    translated_words = translated_batch.split("\n")

    # If we got the same number of translations, use them
    if len(translated_words) == len(batch_words):
        for word, trans in zip(batch_words, translated_words, strict=True):
            translations[word.lower()] = trans.strip()
    else:
        # Fall back to individual translation for this batch
        for word in batch_words:
            translated = argostranslate.translate.translate(word, from_lang, to_lang)
            translations[word.lower()] = translated

    return batch_idx, translations


def _run_batch_translation(
    words_to_translate: list[str],
    from_lang: str,
    to_lang: str,
) -> dict[str, str]:
    """Translate a list of words in batches with progress logging.

    Args:
        words_to_translate: Words needing translation.
        from_lang: Source language code.
        to_lang: Target language code.

    Returns:
        Dict mapping lowercased words to translations.

    Raises:
        RuntimeError: If translation fails.
    """
    new_translations: dict[str, str] = {}
    num_to_translate = len(words_to_translate)

    gpu_status = " (GPU)" if _check_cuda_available() else " (CPU)"
    logger.info(
        "Translating %d words from %s to %s%s...",
        num_to_translate,
        from_lang,
        to_lang,
        gpu_status,
    )

    try:
        batches = [
            words_to_translate[i : i + _BATCH_SIZE]
            for i in range(0, num_to_translate, _BATCH_SIZE)
        ]
        total_batches = len(batches)

        for batch_idx, batch_words in enumerate(batches):
            words_done = min(
                (batch_idx + 1) * _BATCH_SIZE,
                num_to_translate,
            )
            pct = int(words_done / num_to_translate * 100)

            logger.info(
                "  [%3d%%] Translating batch %d/%d " "(%d/%d words)...",
                pct,
                batch_idx + 1,
                total_batches,
                words_done,
                num_to_translate,
            )

            _, batch_translations = _translate_batch_worker(
                batch_words,
                from_lang,
                to_lang,
                batch_idx,
            )
            new_translations.update(batch_translations)

        logger.info("  Translation complete.")
    except Exception as e:
        msg = f"Translation failed for " f"{from_lang} -> {to_lang}: {e}"
        raise RuntimeError(msg) from e

    return new_translations


def translate_words_batch(
    words: Sequence[str],
    from_lang: str,
    to_lang: str,
    *,
    use_cache: bool = True,
) -> list[TranslationResult]:
    """Translate multiple words using argostranslate (offline).

    Uses small batch translation for efficiency with frequent progress updates.
    Requires argostranslate. Will use GPU if CUDA is available.

    Args:
        words: List of words to translate.
        from_lang: Source language code.
        to_lang: Target language code.
        use_cache: Whether to use translation cache.

    Returns:
        List of TranslationResult for each word.

    Raises:
        ImportError: If argostranslate is not available and cannot be installed.
        RuntimeError: If CUDA is available but GPU initialization fails.
    """
    if not words:
        return []

    _ensure_argos_installed()
    _init_gpu_if_available()
    _ensure_language_pair(from_lang, to_lang)

    # Check cache for already-translated words
    cached_results: dict[str, str] = {}
    if use_cache and get_translation_cache is not None:
        cache = get_translation_cache()
        cached_results = cache.get_many(
            list(words),
            from_lang,
            to_lang,
        )

    # Find words that still need translation
    words_to_translate = [word for word in words if word.lower() not in cached_results]

    # Translate uncached words using argos batch
    new_translations: dict[str, str] = {}
    if words_to_translate:
        new_translations = _run_batch_translation(
            words_to_translate,
            from_lang,
            to_lang,
        )

        # Cache new translations
        if use_cache and get_translation_cache is not None:
            get_translation_cache().set_many(
                new_translations,
                from_lang,
                to_lang,
            )

    # Merge cached and new translations
    all_translations = {**cached_results, **new_translations}

    # Build results in original order
    results: list[TranslationResult] = []
    for word in words:
        translation = all_translations.get(word.lower(), "")
        results.append(
            TranslationResult(
                source_word=word,
                translated_word=translation,
                source_lang=from_lang,
                target_lang=to_lang,
                success=bool(translation),
                error=None if translation else "Translation failed",
            )
        )

    return results


if __name__ == "__main__":
    import sys

    sys.exit(main())
