"""Cache classes for vocabulary curve excerpts and Anki decks."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import TYPE_CHECKING, Any

import python_pkg.word_frequency.cache as _cache_mod

if TYPE_CHECKING:
    from pathlib import Path

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
        self.cache_dir = (cache_dir or _cache_mod.get_cache_dir()) / "excerpts"
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
        file_hash = _cache_mod.get_file_hash(filepath)
        cache_path = self._get_cache_path(file_hash, length)

        if not cache_path.exists():
            return None

        try:
            data = json.loads(cache_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, KeyError, OSError):
            return None
        else:
            # Verify hash matches
            if data.get("file_hash") != file_hash:
                return None
            excerpt = data["excerpt"]
            words = list(data["words"])
            return excerpt, words

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
        file_hash = _cache_mod.get_file_hash(filepath)
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


@dataclass(frozen=True)
class AnkiDeckKey:
    """Key parameters for Anki deck cache lookups."""

    filepath: Path
    length: int
    target_lang: str
    include_context: bool
    all_vocab: bool


class AnkiDeckCache:
    """Cache for generated Anki decks."""

    def __init__(self, cache_dir: Path | None = None) -> None:
        """Initialize Anki deck cache.

        Args:
            cache_dir: Optional custom cache directory.
        """
        self.cache_dir = (cache_dir or _cache_mod.get_cache_dir()) / "anki_decks"
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
        *,
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
        key: AnkiDeckKey,
    ) -> tuple[str, str, int, int] | None:
        """Get cached Anki deck.

        Args:
            key: Cache key parameters.

        Returns:
            Tuple of (anki_content, excerpt, num_words, max_rank)
            or None.
        """
        file_hash = _cache_mod.get_file_hash(key.filepath)
        cache_key = self._make_key(
            file_hash,
            key.length,
            key.target_lang,
            include_context=key.include_context,
            all_vocab=key.all_vocab,
        )
        metadata = self._load_metadata()

        if cache_key not in metadata:
            return None

        entry = metadata[cache_key]
        if entry.get("file_hash") != file_hash:
            return None

        deck_file = self.cache_dir / f"{cache_key}.txt"
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
        key: AnkiDeckKey,
        anki_content: str,
        excerpt: str,
        num_words: int,
        max_rank: int,
    ) -> None:
        """Store Anki deck in cache.

        Args:
            key: Cache key parameters.
            anki_content: The Anki deck content.
            excerpt: The excerpt text.
            num_words: Number of words in deck.
            max_rank: Maximum word rank.
        """
        file_hash = _cache_mod.get_file_hash(key.filepath)
        cache_key = self._make_key(
            file_hash,
            key.length,
            key.target_lang,
            include_context=key.include_context,
            all_vocab=key.all_vocab,
        )

        # Save deck content
        deck_file = self.cache_dir / f"{cache_key}.txt"
        deck_file.write_text(anki_content, encoding="utf-8")

        # Update metadata
        metadata = self._load_metadata()
        metadata[cache_key] = {
            "file_hash": file_hash,
            "filepath": str(key.filepath),
            "length": key.length,
            "target_lang": key.target_lang,
            "include_context": key.include_context,
            "all_vocab": key.all_vocab,
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
