"""Tests for word_frequency._cache_decks module."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import patch

if TYPE_CHECKING:
    from pathlib import Path

from python_pkg.word_frequency._cache_decks import (
    AnkiDeckCache,
    AnkiDeckKey,
    VocabCurveCache,
)


class TestVocabCurveCache:
    """Tests for VocabCurveCache."""

    def test_init_creates_dir(self, tmp_path: Path) -> None:
        cache = VocabCurveCache(cache_dir=tmp_path / "sub")
        assert cache.cache_dir.exists()

    def test_get_cache_path(self, tmp_path: Path) -> None:
        cache = VocabCurveCache(cache_dir=tmp_path)
        path = cache._get_cache_path("abcdef1234567890", 10)
        assert path.name == "abcdef1234567890_10.json"

    def test_set_and_get(self, tmp_path: Path) -> None:
        cache = VocabCurveCache(cache_dir=tmp_path)
        fp = tmp_path / "text.txt"
        fp.write_text("hello world", encoding="utf-8")

        cache.set(fp, 10, "hello world", [("hello", 1), ("world", 2)])
        result = cache.get(fp, 10)
        assert result is not None
        excerpt, words = result
        assert excerpt == "hello world"
        assert words == [("hello", 1), ("world", 2)]

    def test_get_not_cached(self, tmp_path: Path) -> None:
        cache = VocabCurveCache(cache_dir=tmp_path)
        fp = tmp_path / "text.txt"
        fp.write_text("hello", encoding="utf-8")
        assert cache.get(fp, 10) is None

    def test_get_corrupt_json(self, tmp_path: Path) -> None:
        cache = VocabCurveCache(cache_dir=tmp_path)
        fp = tmp_path / "text.txt"
        fp.write_text("hello", encoding="utf-8")
        from python_pkg.word_frequency.cache import get_file_hash

        fh = get_file_hash(fp)
        cache_path = cache._get_cache_path(fh, 10)
        cache_path.write_text("not json", encoding="utf-8")
        assert cache.get(fp, 10) is None

    def test_get_hash_mismatch(self, tmp_path: Path) -> None:
        cache = VocabCurveCache(cache_dir=tmp_path)
        fp = tmp_path / "text.txt"
        fp.write_text("hello", encoding="utf-8")
        from python_pkg.word_frequency.cache import get_file_hash

        fh = get_file_hash(fp)
        cache_path = cache._get_cache_path(fh, 10)
        data = {
            "file_hash": "wrong_hash",
            "excerpt": "hello",
            "words": [],
        }
        cache_path.write_text(json.dumps(data), encoding="utf-8")
        assert cache.get(fp, 10) is None

    def test_clear(self, tmp_path: Path) -> None:
        cache = VocabCurveCache(cache_dir=tmp_path)
        fp = tmp_path / "text.txt"
        fp.write_text("hello", encoding="utf-8")
        cache.set(fp, 10, "hello", [("hello", 1)])
        cache.clear()
        assert cache.get(fp, 10) is None

    def test_stats(self, tmp_path: Path) -> None:
        cache = VocabCurveCache(cache_dir=tmp_path)
        fp = tmp_path / "text.txt"
        fp.write_text("hello", encoding="utf-8")
        cache.set(fp, 10, "hello", [("hello", 1)])
        stats = cache.stats()
        assert stats["total_entries"] == 1
        assert stats["cache_size_bytes"] > 0

    def test_stats_empty(self, tmp_path: Path) -> None:
        cache = VocabCurveCache(cache_dir=tmp_path)
        stats = cache.stats()
        assert stats["total_entries"] == 0


class TestAnkiDeckCache:
    """Tests for AnkiDeckCache."""

    def test_init_creates_dir(self, tmp_path: Path) -> None:
        cache = AnkiDeckCache(cache_dir=tmp_path / "sub")
        assert cache.cache_dir.exists()

    def test_make_key(self) -> None:
        key = AnkiDeckCache._make_key(
            "abcdef1234567890hash",
            10,
            "es",
            include_context=True,
            all_vocab=False,
        )
        assert "abcdef1234567890" in key
        assert "10" in key
        assert "es" in key
        assert "ctx1" in key
        assert "all0" in key

    def test_set_and_get(self, tmp_path: Path) -> None:
        cache = AnkiDeckCache(cache_dir=tmp_path)
        fp = tmp_path / "text.txt"
        fp.write_text("hello world", encoding="utf-8")

        dk = AnkiDeckKey(
            filepath=fp,
            length=10,
            target_lang="es",
            include_context=False,
            all_vocab=True,
        )
        cache.set(dk, "deck content", "hello world", 2, 5)
        result = cache.get(dk)
        assert result is not None
        content, excerpt, num_words, max_rank = result
        assert content == "deck content"
        assert excerpt == "hello world"
        assert num_words == 2
        assert max_rank == 5

    def test_get_not_cached(self, tmp_path: Path) -> None:
        cache = AnkiDeckCache(cache_dir=tmp_path)
        fp = tmp_path / "text.txt"
        fp.write_text("hello", encoding="utf-8")
        dk = AnkiDeckKey(fp, 10, "es", include_context=False, all_vocab=True)
        assert cache.get(dk) is None

    def test_get_hash_mismatch(self, tmp_path: Path) -> None:
        cache = AnkiDeckCache(cache_dir=tmp_path)
        fp = tmp_path / "text.txt"
        fp.write_text("hello", encoding="utf-8")
        dk = AnkiDeckKey(fp, 10, "es", include_context=False, all_vocab=True)
        cache.set(dk, "content", "hello", 1, 1)
        # Modify file to change hash
        fp.write_text("changed content", encoding="utf-8")
        assert cache.get(dk) is None

    def test_get_stored_hash_mismatch(self, tmp_path: Path) -> None:
        """Metadata entry exists under the right key but stored hash differs."""
        cache = AnkiDeckCache(cache_dir=tmp_path)
        fp = tmp_path / "text.txt"
        fp.write_text("hello", encoding="utf-8")
        dk = AnkiDeckKey(fp, 10, "es", include_context=False, all_vocab=True)
        cache.set(dk, "content", "hello", 1, 1)
        # Tamper with stored hash in metadata
        m = cache._load_metadata()
        for entry in m.values():
            entry["file_hash"] = "tampered"
        cache._metadata = m
        cache._save_metadata()
        assert cache.get(dk) is None

    def test_get_missing_deck_file(self, tmp_path: Path) -> None:
        cache = AnkiDeckCache(cache_dir=tmp_path)
        fp = tmp_path / "text.txt"
        fp.write_text("hello", encoding="utf-8")
        dk = AnkiDeckKey(fp, 10, "es", include_context=False, all_vocab=True)
        cache.set(dk, "content", "hello", 1, 1)
        # Remove all .txt files in cache dir
        for f in cache.cache_dir.glob("*.txt"):
            f.unlink()
        assert cache.get(dk) is None

    def test_get_oserror_on_read(self, tmp_path: Path) -> None:
        cache = AnkiDeckCache(cache_dir=tmp_path)
        fp = tmp_path / "text.txt"
        fp.write_text("hello", encoding="utf-8")
        dk = AnkiDeckKey(fp, 10, "es", include_context=False, all_vocab=True)
        cache.set(dk, "content", "hello", 1, 1)
        # Mock read_text to raise OSError
        with patch("pathlib.Path.read_text", side_effect=OSError("read error")):
            assert cache.get(dk) is None

    def test_load_metadata_corrupt(self, tmp_path: Path) -> None:
        cache = AnkiDeckCache(cache_dir=tmp_path)
        cache.metadata_file.write_text("not json", encoding="utf-8")
        metadata = cache._load_metadata()
        assert metadata == {}

    def test_load_metadata_cached(self, tmp_path: Path) -> None:
        cache = AnkiDeckCache(cache_dir=tmp_path)
        cache._metadata = {"key": "val"}
        assert cache._load_metadata() == {"key": "val"}

    def test_save_metadata_none(self, tmp_path: Path) -> None:
        cache = AnkiDeckCache(cache_dir=tmp_path)
        cache._metadata = None
        cache._save_metadata()
        assert not cache.metadata_file.exists()

    def test_clear(self, tmp_path: Path) -> None:
        cache = AnkiDeckCache(cache_dir=tmp_path)
        fp = tmp_path / "text.txt"
        fp.write_text("hello", encoding="utf-8")
        dk = AnkiDeckKey(fp, 10, "es", include_context=False, all_vocab=True)
        cache.set(dk, "content", "hello", 1, 1)
        cache.clear()
        assert cache.get(dk) is None
        assert not cache.metadata_file.exists()

    def test_clear_no_metadata_file(self, tmp_path: Path) -> None:
        cache = AnkiDeckCache(cache_dir=tmp_path)
        cache.clear()

    def test_stats(self, tmp_path: Path) -> None:
        cache = AnkiDeckCache(cache_dir=tmp_path)
        fp = tmp_path / "text.txt"
        fp.write_text("hello", encoding="utf-8")
        dk = AnkiDeckKey(fp, 10, "es", include_context=False, all_vocab=True)
        cache.set(dk, "content", "hello", 1, 1)
        stats = cache.stats()
        assert stats["total_entries"] == 1
        assert stats["cache_size_bytes"] > 0

    def test_stats_empty(self, tmp_path: Path) -> None:
        cache = AnkiDeckCache(cache_dir=tmp_path)
        stats = cache.stats()
        assert stats["total_entries"] == 0
        assert stats["cache_size_bytes"] == 0
