"""Tests for word_frequency.cache module."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import patch

if TYPE_CHECKING:
    from pathlib import Path

from python_pkg.word_frequency.cache import (
    TranslationCache,
    _CacheHolder,
    clear_all_caches,
    get_all_cache_stats,
    get_anki_deck_cache,
    get_cache_dir,
    get_file_hash,
    get_text_hash,
    get_translation_cache,
    get_vocab_curve_cache,
    main,
)


class TestGetCacheDir:
    """Tests for get_cache_dir."""

    def test_returns_default(self, tmp_path: Path) -> None:
        with (
            patch("python_pkg.word_frequency.cache.DEFAULT_CACHE_DIR", tmp_path),
            patch.dict("os.environ", {}, clear=False),
        ):
            d = get_cache_dir()
        assert d == tmp_path

    def test_respects_env_var(self, tmp_path: Path) -> None:
        custom = tmp_path / "custom_cache"
        with patch.dict("os.environ", {"WORD_FREQ_CACHE_DIR": str(custom)}):
            d = get_cache_dir()
        assert d == custom
        assert d.exists()


class TestGetFileHash:
    """Tests for get_file_hash."""

    def test_computes_hash(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("hello", encoding="utf-8")
        h = get_file_hash(f)
        assert isinstance(h, str)
        assert len(h) == 64

    def test_different_content_different_hash(self, tmp_path: Path) -> None:
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        f1.write_text("hello", encoding="utf-8")
        f2.write_text("world", encoding="utf-8")
        assert get_file_hash(f1) != get_file_hash(f2)


class TestGetTextHash:
    """Tests for get_text_hash."""

    def test_computes_hash(self) -> None:
        h = get_text_hash("hello")
        assert isinstance(h, str)
        assert len(h) == 64


class TestTranslationCache:
    """Tests for TranslationCache."""

    def test_set_and_get(self, tmp_path: Path) -> None:
        cache = TranslationCache(cache_dir=tmp_path)
        cache.set("hello", "en", "es", "hola")
        assert cache.get("hello", "en", "es") == "hola"

    def test_get_missing(self, tmp_path: Path) -> None:
        cache = TranslationCache(cache_dir=tmp_path)
        assert cache.get("missing", "en", "es") is None

    def test_flush(self, tmp_path: Path) -> None:
        cache = TranslationCache(cache_dir=tmp_path)
        cache.set("hello", "en", "es", "hola")
        cache.flush()
        assert cache.cache_file.exists()
        data = json.loads(cache.cache_file.read_text(encoding="utf-8"))
        assert "en:es:hello" in data

    def test_auto_save(self, tmp_path: Path) -> None:
        cache = TranslationCache(cache_dir=tmp_path)
        cache.set("hello", "en", "es", "hola", auto_save=True)
        assert cache.cache_file.exists()

    def test_load_from_disk(self, tmp_path: Path) -> None:
        cache1 = TranslationCache(cache_dir=tmp_path)
        cache1.set("hello", "en", "es", "hola", auto_save=True)
        cache2 = TranslationCache(cache_dir=tmp_path)
        assert cache2.get("hello", "en", "es") == "hola"

    def test_load_corrupt_json(self, tmp_path: Path) -> None:
        cache_file = tmp_path / "translations.json"
        cache_file.write_text("not json", encoding="utf-8")
        cache = TranslationCache(cache_dir=tmp_path)
        assert cache.get("hello", "en", "es") is None

    def test_save_not_dirty(self, tmp_path: Path) -> None:
        cache = TranslationCache(cache_dir=tmp_path)
        cache._load_cache()
        cache._save_cache()
        assert not cache.cache_file.exists()

    def test_get_many(self, tmp_path: Path) -> None:
        cache = TranslationCache(cache_dir=tmp_path)
        cache.set("hello", "en", "es", "hola")
        cache.set("world", "en", "es", "mundo")
        result = cache.get_many(["hello", "world", "missing"], "en", "es")
        assert result == {"hello": "hola", "world": "mundo"}

    def test_set_many(self, tmp_path: Path) -> None:
        cache = TranslationCache(cache_dir=tmp_path)
        cache.set_many({"hello": "hola", "world": "mundo"}, "en", "es")
        assert cache.get("hello", "en", "es") == "hola"
        assert cache.get("world", "en", "es") == "mundo"
        assert cache.cache_file.exists()

    def test_clear(self, tmp_path: Path) -> None:
        cache = TranslationCache(cache_dir=tmp_path)
        cache.set("hello", "en", "es", "hola", auto_save=True)
        cache.clear()
        assert cache.get("hello", "en", "es") is None
        assert not cache.cache_file.exists()

    def test_clear_no_file(self, tmp_path: Path) -> None:
        cache = TranslationCache(cache_dir=tmp_path)
        cache.clear()

    def test_stats(self, tmp_path: Path) -> None:
        cache = TranslationCache(cache_dir=tmp_path)
        cache.set("hello", "en", "es", "hola", auto_save=True)
        stats = cache.stats()
        assert stats["total_entries"] == 1
        assert stats["cache_size_bytes"] > 0

    def test_stats_no_file(self, tmp_path: Path) -> None:
        cache = TranslationCache(cache_dir=tmp_path)
        stats = cache.stats()
        assert stats["total_entries"] == 0
        assert stats["cache_size_bytes"] == 0


class TestGlobalCaches:
    """Tests for global cache singletons."""

    def test_get_translation_cache(self, tmp_path: Path) -> None:
        _CacheHolder.translation = None
        with patch(
            "python_pkg.word_frequency.cache.get_cache_dir", return_value=tmp_path
        ):
            c = get_translation_cache()
        assert isinstance(c, TranslationCache)
        _CacheHolder.translation = None

    def test_get_vocab_curve_cache(self, tmp_path: Path) -> None:
        _CacheHolder.vocab_curve = None
        with patch(
            "python_pkg.word_frequency.cache.get_cache_dir", return_value=tmp_path
        ):
            c = get_vocab_curve_cache()
        assert c is not None
        _CacheHolder.vocab_curve = None

    def test_get_vocab_curve_cache_already_set(self, tmp_path: Path) -> None:
        from python_pkg.word_frequency._cache_decks import VocabCurveCache

        existing = VocabCurveCache(cache_dir=tmp_path)
        _CacheHolder.vocab_curve = existing
        c = get_vocab_curve_cache()
        assert c is existing
        _CacheHolder.vocab_curve = None

    def test_get_anki_deck_cache(self, tmp_path: Path) -> None:
        _CacheHolder.anki_deck = None
        with patch(
            "python_pkg.word_frequency.cache.get_cache_dir", return_value=tmp_path
        ):
            c = get_anki_deck_cache()
        assert c is not None
        _CacheHolder.anki_deck = None

    def test_clear_all_caches(self, tmp_path: Path) -> None:
        _CacheHolder.translation = None
        _CacheHolder.vocab_curve = None
        _CacheHolder.anki_deck = None
        with patch(
            "python_pkg.word_frequency.cache.get_cache_dir", return_value=tmp_path
        ):
            clear_all_caches()
        _CacheHolder.translation = None
        _CacheHolder.vocab_curve = None
        _CacheHolder.anki_deck = None

    def test_get_all_cache_stats(self, tmp_path: Path) -> None:
        _CacheHolder.translation = None
        _CacheHolder.vocab_curve = None
        _CacheHolder.anki_deck = None
        with patch(
            "python_pkg.word_frequency.cache.get_cache_dir", return_value=tmp_path
        ):
            stats = get_all_cache_stats()
        assert "translations" in stats
        assert "vocab_curves" in stats
        assert "anki_decks" in stats
        _CacheHolder.translation = None
        _CacheHolder.vocab_curve = None
        _CacheHolder.anki_deck = None


class TestMain:
    """Tests for cache CLI main function."""

    def test_stats_default(self, tmp_path: Path) -> None:
        _CacheHolder.translation = None
        _CacheHolder.vocab_curve = None
        _CacheHolder.anki_deck = None
        with (
            patch(
                "python_pkg.word_frequency.cache.get_cache_dir", return_value=tmp_path
            ),
            patch("sys.argv", ["cache"]),
        ):
            result = main()
        assert result == 0
        _CacheHolder.translation = None
        _CacheHolder.vocab_curve = None
        _CacheHolder.anki_deck = None

    def test_clear(self, tmp_path: Path) -> None:
        _CacheHolder.translation = None
        _CacheHolder.vocab_curve = None
        _CacheHolder.anki_deck = None
        with (
            patch(
                "python_pkg.word_frequency.cache.get_cache_dir", return_value=tmp_path
            ),
            patch("sys.argv", ["cache", "--clear"]),
        ):
            result = main()
        assert result == 0
        _CacheHolder.translation = None
        _CacheHolder.vocab_curve = None
        _CacheHolder.anki_deck = None

    def test_clear_translations(self, tmp_path: Path) -> None:
        _CacheHolder.translation = None
        with (
            patch(
                "python_pkg.word_frequency.cache.get_cache_dir", return_value=tmp_path
            ),
            patch("sys.argv", ["cache", "--clear-translations"]),
        ):
            result = main()
        assert result == 0
        _CacheHolder.translation = None

    def test_clear_excerpts(self, tmp_path: Path) -> None:
        _CacheHolder.vocab_curve = None
        with (
            patch(
                "python_pkg.word_frequency.cache.get_cache_dir", return_value=tmp_path
            ),
            patch("sys.argv", ["cache", "--clear-excerpts"]),
        ):
            result = main()
        assert result == 0
        _CacheHolder.vocab_curve = None

    def test_clear_anki(self, tmp_path: Path) -> None:
        _CacheHolder.anki_deck = None
        with (
            patch(
                "python_pkg.word_frequency.cache.get_cache_dir", return_value=tmp_path
            ),
            patch("sys.argv", ["cache", "--clear-anki"]),
        ):
            result = main()
        assert result == 0
        _CacheHolder.anki_deck = None

    def test_stats_with_data(self, tmp_path: Path) -> None:
        _CacheHolder.translation = None
        _CacheHolder.vocab_curve = None
        _CacheHolder.anki_deck = None
        with patch(
            "python_pkg.word_frequency.cache.get_cache_dir", return_value=tmp_path
        ):
            tc = get_translation_cache()
            tc.set("a", "en", "es", "b", auto_save=True)
            with patch("sys.argv", ["cache", "--stats"]):
                result = main()
        assert result == 0
        _CacheHolder.translation = None
        _CacheHolder.vocab_curve = None
        _CacheHolder.anki_deck = None

    def test_stats_size_kb(self, tmp_path: Path) -> None:
        _CacheHolder.translation = None
        _CacheHolder.vocab_curve = None
        _CacheHolder.anki_deck = None
        with patch(
            "python_pkg.word_frequency.cache.get_cache_dir", return_value=tmp_path
        ):
            tc = get_translation_cache()
            # Write enough data to push size over 1 KB
            for i in range(50):
                tc.set(f"word_{i}_long_enough", "en", "es", f"translation_{i}_long")
            tc.flush()
            with patch("sys.argv", ["cache", "--stats"]):
                result = main()
        assert result == 0
        _CacheHolder.translation = None
        _CacheHolder.vocab_curve = None
        _CacheHolder.anki_deck = None

    def test_stats_size_mb(self, tmp_path: Path) -> None:
        _CacheHolder.translation = None
        _CacheHolder.vocab_curve = None
        _CacheHolder.anki_deck = None
        with patch(
            "python_pkg.word_frequency.cache.get_cache_dir", return_value=tmp_path
        ):
            tc = get_translation_cache()
            tc.set("x", "en", "es", "y", auto_save=True)
            # Inflate cache file beyond 1 MB
            tc.cache_file.write_text("x" * (1024 * 1024 + 1), encoding="utf-8")
            with patch("sys.argv", ["cache", "--stats"]):
                result = main()
        assert result == 0
        _CacheHolder.translation = None
        _CacheHolder.vocab_curve = None
        _CacheHolder.anki_deck = None
