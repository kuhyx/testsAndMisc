#!/usr/bin/env python3
"""Caching utilities for word frequency analysis.

Provides disk-based caching for:
- Translations (word -> translation mappings)
- Vocabulary curve excerpts (file + length -> excerpt + words)
- Generated Anki decks

Cache location: ~/.cache/word_frequency/
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

# Default cache directory
DEFAULT_CACHE_DIR = Path.home() / ".cache" / "word_frequency"


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
    with open(filepath, "rb") as f:
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
                    self._cache = json.loads(self.cache_file.read_text(encoding="utf-8"))
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

    def get(
        self, word: str, source_lang: str, target_lang: str
    ) -> str | None:
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
        self, word: str, source_lang: str, target_lang: str, translation: str,
        *, auto_save: bool = False,
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
# Vocabulary Curve Cache
# =============================================================================


class VocabCurveCache:
    """Cache for vocabulary curve analysis results."""

    def __init__(self, cache_dir: Path | None = None) -> None:
        """Initialize vocabulary curve cache.

        Args:
            cache_dir: Optional custom cache directory.
        """
        self.cache_dir = (cache_dir or get_cache_dir()) / "excerpts"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, file_hash: str, length: int) -> Path:
        """Get path to cache file for given hash and length.

        Args:
            file_hash: Hash of source file.
            length: Excerpt length.

        Returns:
            Path to cache file.
        """
        return self.cache_dir / f"{file_hash[:16]}_{length}.json"

    def get(
        self, filepath: Path, length: int
    ) -> tuple[str, list[tuple[str, int]]] | None:
        """Get cached excerpt and words for a file and length.

        Args:
            filepath: Path to source file.
            length: Excerpt length.

        Returns:
            Tuple of (excerpt, words_with_ranks) or None if not cached.
        """
        file_hash = get_file_hash(filepath)
        cache_path = self._get_cache_path(file_hash, length)

        if not cache_path.exists():
            return None

        try:
            data = json.loads(cache_path.read_text(encoding="utf-8"))
            # Verify hash matches
            if data.get("file_hash") != file_hash:
                return None
            excerpt = data["excerpt"]
            words = [(w, r) for w, r in data["words"]]
            return excerpt, words
        except (json.JSONDecodeError, KeyError, OSError):
            return None

    def set(
        self,
        filepath: Path,
        length: int,
        excerpt: str,
        words: list[tuple[str, int]],
    ) -> None:
        """Store excerpt and words in cache.

        Args:
            filepath: Path to source file.
            length: Excerpt length.
            excerpt: The excerpt text.
            words: List of (word, rank) tuples.
        """
        file_hash = get_file_hash(filepath)
        cache_path = self._get_cache_path(file_hash, length)

        data = {
            "file_hash": file_hash,
            "filepath": str(filepath),
            "length": length,
            "excerpt": excerpt,
            "words": [[w, r] for w, r in words],
        }

        cache_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def clear(self) -> None:
        """Clear all cached excerpts."""
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()

    def stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dict with cache stats.
        """
        cache_files = list(self.cache_dir.glob("*.json"))
        total_size = sum(f.stat().st_size for f in cache_files)
        return {
            "total_entries": len(cache_files),
            "cache_dir": str(self.cache_dir),
            "cache_size_bytes": total_size,
        }


# =============================================================================
# Anki Deck Cache
# =============================================================================


class AnkiDeckCache:
    """Cache for generated Anki decks."""

    def __init__(self, cache_dir: Path | None = None) -> None:
        """Initialize Anki deck cache.

        Args:
            cache_dir: Optional custom cache directory.
        """
        self.cache_dir = (cache_dir or get_cache_dir()) / "anki_decks"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.cache_dir / "metadata.json"
        self._metadata: dict[str, Any] | None = None

    def _load_metadata(self) -> dict[str, Any]:
        """Load metadata from disk."""
        if self._metadata is None:
            if self.metadata_file.exists():
                try:
                    self._metadata = json.loads(
                        self.metadata_file.read_text(encoding="utf-8")
                    )
                except (json.JSONDecodeError, OSError):
                    self._metadata = {}
            else:
                self._metadata = {}
        return self._metadata

    def _save_metadata(self) -> None:
        """Save metadata to disk."""
        if self._metadata is not None:
            self.metadata_file.write_text(
                json.dumps(self._metadata, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    @staticmethod
    def _make_key(
        file_hash: str,
        length: int,
        target_lang: str,
        include_context: bool,
        all_vocab: bool,
    ) -> str:
        """Create cache key for an Anki deck.

        Args:
            file_hash: Hash of source file.
            length: Excerpt length.
            target_lang: Target language.
            include_context: Whether context is included.
            all_vocab: Whether all vocab is included.

        Returns:
            Cache key string.
        """
        flags = f"ctx{int(include_context)}_all{int(all_vocab)}"
        return f"{file_hash[:16]}_{length}_{target_lang}_{flags}"

    def get(
        self,
        filepath: Path,
        length: int,
        target_lang: str,
        include_context: bool,
        all_vocab: bool,
    ) -> tuple[str, str, int, int] | None:
        """Get cached Anki deck.

        Args:
            filepath: Path to source file.
            length: Excerpt length.
            target_lang: Target language.
            include_context: Whether context is included.
            all_vocab: Whether all vocab is included.

        Returns:
            Tuple of (anki_content, excerpt, num_words, max_rank) or None.
        """
        file_hash = get_file_hash(filepath)
        key = self._make_key(file_hash, length, target_lang, include_context, all_vocab)
        metadata = self._load_metadata()

        if key not in metadata:
            return None

        entry = metadata[key]
        if entry.get("file_hash") != file_hash:
            return None

        deck_file = self.cache_dir / f"{key}.txt"
        if not deck_file.exists():
            return None

        try:
            content = deck_file.read_text(encoding="utf-8")
            return (
                content,
                entry["excerpt"],
                entry["num_words"],
                entry["max_rank"],
            )
        except OSError:
            return None

    def set(
        self,
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
            anki_content: The Anki deck content.
            excerpt: The excerpt text.
            num_words: Number of words in deck.
            max_rank: Maximum word rank.
        """
        file_hash = get_file_hash(filepath)
        key = self._make_key(file_hash, length, target_lang, include_context, all_vocab)

        # Save deck content
        deck_file = self.cache_dir / f"{key}.txt"
        deck_file.write_text(anki_content, encoding="utf-8")

        # Update metadata
        metadata = self._load_metadata()
        metadata[key] = {
            "file_hash": file_hash,
            "filepath": str(filepath),
            "length": length,
            "target_lang": target_lang,
            "include_context": include_context,
            "all_vocab": all_vocab,
            "excerpt": excerpt,
            "num_words": num_words,
            "max_rank": max_rank,
        }
        self._save_metadata()

    def clear(self) -> None:
        """Clear all cached decks."""
        self._metadata = {}
        for cache_file in self.cache_dir.glob("*.txt"):
            cache_file.unlink()
        if self.metadata_file.exists():
            self.metadata_file.unlink()

    def stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dict with cache stats.
        """
        metadata = self._load_metadata()
        cache_files = list(self.cache_dir.glob("*.txt"))
        total_size = sum(f.stat().st_size for f in cache_files)
        return {
            "total_entries": len(metadata),
            "cache_dir": str(self.cache_dir),
            "cache_size_bytes": total_size,
        }


# =============================================================================
# Global Cache Instances
# =============================================================================

# Singleton instances
_translation_cache: TranslationCache | None = None
_vocab_curve_cache: VocabCurveCache | None = None
_anki_deck_cache: AnkiDeckCache | None = None


def get_translation_cache() -> TranslationCache:
    """Get the global translation cache instance."""
    global _translation_cache  # noqa: PLW0603
    if _translation_cache is None:
        _translation_cache = TranslationCache()
    return _translation_cache


def get_vocab_curve_cache() -> VocabCurveCache:
    """Get the global vocabulary curve cache instance."""
    global _vocab_curve_cache  # noqa: PLW0603
    if _vocab_curve_cache is None:
        _vocab_curve_cache = VocabCurveCache()
    return _vocab_curve_cache


def get_anki_deck_cache() -> AnkiDeckCache:
    """Get the global Anki deck cache instance."""
    global _anki_deck_cache  # noqa: PLW0603
    if _anki_deck_cache is None:
        _anki_deck_cache = AnkiDeckCache()
    return _anki_deck_cache


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
    import argparse

    parser = argparse.ArgumentParser(description="Manage word frequency caches")
    parser.add_argument(
        "--stats", action="store_true", help="Show cache statistics"
    )
    parser.add_argument(
        "--clear", action="store_true", help="Clear all caches"
    )
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
        print("All caches cleared.")  # noqa: T201
        return 0

    if args.clear_translations:
        get_translation_cache().clear()
        print("Translation cache cleared.")  # noqa: T201
        return 0

    if args.clear_excerpts:
        get_vocab_curve_cache().clear()
        print("Excerpt cache cleared.")  # noqa: T201
        return 0

    if args.clear_anki:
        get_anki_deck_cache().clear()
        print("Anki deck cache cleared.")  # noqa: T201
        return 0

    # Default: show stats
    stats = get_all_cache_stats()
    print("Cache Statistics")  # noqa: T201
    print("=" * 50)  # noqa: T201
    for cache_name, cache_stats in stats.items():
        print(f"\n{cache_name.upper()}:")  # noqa: T201
        for key, value in cache_stats.items():
            if key == "cache_size_bytes":
                # Format as human-readable
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


if __name__ == "__main__":
    import sys
    sys.exit(main())
