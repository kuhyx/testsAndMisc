#!/usr/bin/env python3
"""Caching utilities for word frequency analysis.

Provides disk-based caching for:
- Translations (word -> translation mappings)
- Vocabulary curve excerpts (file + length -> excerpt + words)
- Generated Anki decks

Cache location: ~/.cache/word_frequency/
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any

from python_pkg.word_frequency._cache_decks import (
    AnkiDeckCache,
    AnkiDeckKey,
    VocabCurveCache,
)

__all__ = ["AnkiDeckCache", "AnkiDeckKey", "VocabCurveCache"]

logger = logging.getLogger(__name__)

# Default cache directory
DEFAULT_CACHE_DIR = Path.home() / ".cache" / "word_frequency"

_ONE_KB = 1024
_ONE_MB = 1024 * 1024


def get_cache_dir() -> Path:
    """Get the cache directory, creating it if needed.

    Returns:
        Path to cache directory.
    """
    cache_dir = Path(os.environ.get("WORD_FREQ_CACHE_DIR", str(DEFAULT_CACHE_DIR)))
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_file_hash(filepath: Path) -> str:
    """Compute SHA256 hash of a file's contents.

    Args:
        filepath: Path to file.

    Returns:
        Hex digest of file hash.
    """
    hasher = hashlib.sha256()
    with filepath.open("rb") as f:
        # Read in chunks for large files
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def get_text_hash(text: str) -> str:
    """Compute SHA256 hash of text content.

    Args:
        text: Text to hash.

    Returns:
        Hex digest of text hash.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# =============================================================================
# Translation Cache
# =============================================================================


class TranslationCache:
    """Cache for word translations."""

    def __init__(self, cache_dir: Path | None = None) -> None:
        """Initialize translation cache.

        Args:
            cache_dir: Optional custom cache directory.
        """
        self.cache_dir = cache_dir or get_cache_dir()
        self.cache_file = self.cache_dir / "translations.json"
        self._cache: dict[str, str] | None = None
        self._dirty = False  # Track if cache needs saving

    def _load_cache(self) -> dict[str, str]:
        """Load cache from disk."""
        if self._cache is None:
            if self.cache_file.exists():
                try:
                    self._cache = json.loads(
                        self.cache_file.read_text(encoding="utf-8")
                    )
                except (json.JSONDecodeError, OSError):
                    self._cache = {}
            else:
                self._cache = {}
        return self._cache

    def _save_cache(self) -> None:
        """Save cache to disk if dirty."""
        if self._cache is not None and self._dirty:
            self.cache_file.write_text(
                json.dumps(self._cache, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            self._dirty = False

    def flush(self) -> None:
        """Force save cache to disk."""
        self._save_cache()

    @staticmethod
    def _make_key(word: str, source_lang: str, target_lang: str) -> str:
        """Create cache key for a translation.

        Args:
            word: Word to translate.
            source_lang: Source language code.
            target_lang: Target language code.

        Returns:
            Cache key string.
        """
        return f"{source_lang}:{target_lang}:{word.lower()}"

    def get(self, word: str, source_lang: str, target_lang: str) -> str | None:
        """Get cached translation.

        Args:
            word: Word to look up.
            source_lang: Source language code.
            target_lang: Target language code.

        Returns:
            Cached translation or None if not found.
        """
        cache = self._load_cache()
        key = self._make_key(word, source_lang, target_lang)
        return cache.get(key)

    def set(
        self,
        word: str,
        source_lang: str,
        target_lang: str,
        translation: str,
        *,
        auto_save: bool = False,
    ) -> None:
        """Store translation in cache.

        Args:
            word: Original word.
            source_lang: Source language code.
            target_lang: Target language code.
            translation: Translated word.
            auto_save: If True, save to disk immediately.
        """
        cache = self._load_cache()
        key = self._make_key(word, source_lang, target_lang)
        cache[key] = translation
        self._dirty = True
        if auto_save:
            self._save_cache()

    def get_many(
        self, words: list[str], source_lang: str, target_lang: str
    ) -> dict[str, str]:
        """Get multiple cached translations.

        Args:
            words: Words to look up.
            source_lang: Source language code.
            target_lang: Target language code.

        Returns:
            Dict mapping words to their cached translations.
        """
        cache = self._load_cache()
        result: dict[str, str] = {}
        for word in words:
            key = self._make_key(word, source_lang, target_lang)
            if key in cache:
                result[word.lower()] = cache[key]
        return result

    def set_many(
        self,
        translations: dict[str, str],
        source_lang: str,
        target_lang: str,
    ) -> None:
        """Store multiple translations in cache and save to disk.

        Args:
            translations: Dict mapping words to translations.
            source_lang: Source language code.
            target_lang: Target language code.
        """
        cache = self._load_cache()
        for word, translation in translations.items():
            key = self._make_key(word, source_lang, target_lang)
            cache[key] = translation
        self._dirty = True
        self._save_cache()  # Save once after all additions

    def clear(self) -> None:
        """Clear all cached translations."""
        self._cache = {}
        self._dirty = False
        if self.cache_file.exists():
            self.cache_file.unlink()

    def stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dict with cache stats.
        """
        cache = self._load_cache()
        return {
            "total_entries": len(cache),
            "cache_file": str(self.cache_file),
            "cache_size_bytes": (
                self.cache_file.stat().st_size if self.cache_file.exists() else 0
            ),
        }


# =============================================================================
# Global Cache Instances
# =============================================================================


class _CacheHolder:
    """Holds singleton cache instances."""

    translation: TranslationCache | None = None
    vocab_curve: VocabCurveCache | None = None
    anki_deck: AnkiDeckCache | None = None


def get_translation_cache() -> TranslationCache:
    """Get the global translation cache instance."""
    if _CacheHolder.translation is None:
        _CacheHolder.translation = TranslationCache()
    return _CacheHolder.translation


def get_vocab_curve_cache() -> VocabCurveCache:
    """Get the global vocabulary curve cache instance."""
    if _CacheHolder.vocab_curve is None:
        _CacheHolder.vocab_curve = VocabCurveCache()
    return _CacheHolder.vocab_curve


def get_anki_deck_cache() -> AnkiDeckCache:
    """Get the global Anki deck cache instance."""
    if _CacheHolder.anki_deck is None:
        _CacheHolder.anki_deck = AnkiDeckCache()
    return _CacheHolder.anki_deck


def clear_all_caches() -> None:
    """Clear all caches."""
    get_translation_cache().clear()
    get_vocab_curve_cache().clear()
    get_anki_deck_cache().clear()


def get_all_cache_stats() -> dict[str, dict[str, Any]]:
    """Get statistics for all caches.

    Returns:
        Dict with stats for each cache type.
    """
    return {
        "translations": get_translation_cache().stats(),
        "vocab_curves": get_vocab_curve_cache().stats(),
        "anki_decks": get_anki_deck_cache().stats(),
    }


def main() -> int:
    """CLI for cache management.

    Returns:
        Exit code.
    """
    parser = argparse.ArgumentParser(description="Manage word frequency caches")
    parser.add_argument("--stats", action="store_true", help="Show cache statistics")
    parser.add_argument("--clear", action="store_true", help="Clear all caches")
    parser.add_argument(
        "--clear-translations", action="store_true", help="Clear translation cache"
    )
    parser.add_argument(
        "--clear-excerpts", action="store_true", help="Clear excerpt cache"
    )
    parser.add_argument(
        "--clear-anki", action="store_true", help="Clear Anki deck cache"
    )

    args = parser.parse_args()

    if args.clear:
        clear_all_caches()
        logger.info("All caches cleared.")
        return 0

    if args.clear_translations:
        get_translation_cache().clear()
        logger.info("Translation cache cleared.")
        return 0

    if args.clear_excerpts:
        get_vocab_curve_cache().clear()
        logger.info("Excerpt cache cleared.")
        return 0

    if args.clear_anki:
        get_anki_deck_cache().clear()
        logger.info("Anki deck cache cleared.")
        return 0

    # Default: show stats
    stats = get_all_cache_stats()
    logger.info("Cache Statistics")
    logger.info("=" * 50)
    for cache_name, cache_stats in stats.items():
        logger.info("\n%s:", cache_name.upper())
        for key, value in cache_stats.items():
            if key == "cache_size_bytes":
                # Format as human-readable
                if value < _ONE_KB:
                    size_str = f"{value} B"
                elif value < _ONE_MB:
                    size_str = f"{value / _ONE_KB:.1f} KB"
                else:
                    size_str = f"{value / _ONE_MB:.1f} MB"
                logger.info("  %s: %s", key, size_str)
            else:
                logger.info("  %s: %s", key, value)

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
