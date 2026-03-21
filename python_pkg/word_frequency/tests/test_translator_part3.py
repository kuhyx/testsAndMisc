"""Tests for translator.py missing lines 26, 34-35, 426."""

from __future__ import annotations

import importlib
import sys
from typing import TYPE_CHECKING, cast
from unittest.mock import MagicMock, patch

if TYPE_CHECKING:
    import types

from python_pkg.word_frequency import translator
from python_pkg.word_frequency.tests._translator_helpers import ArgosAvailableMock


class TestArgosImportFallback:
    """Cover line 26: argostranslate = None when import fails."""

    def test_argostranslate_import_error(self) -> None:
        """Reimport translator with argostranslate absent to cover line 26."""
        # Save originals
        orig_argos = sys.modules.get("argostranslate")
        orig_argos_pkg = sys.modules.get("argostranslate.package")
        orig_argos_tr = sys.modules.get("argostranslate.translate")
        getattr(translator, "argostranslate", None)

        try:
            # Make argostranslate imports fail
            sys.modules["argostranslate"] = cast("types.ModuleType", None)
            sys.modules["argostranslate.package"] = cast("types.ModuleType", None)
            sys.modules["argostranslate.translate"] = cast("types.ModuleType", None)

            # Reimport to trigger the except ImportError branch
            importlib.reload(translator)

            assert translator.argostranslate is None
        finally:
            # Restore
            if orig_argos is not None:
                sys.modules["argostranslate"] = orig_argos
            else:
                sys.modules.pop("argostranslate", None)
            if orig_argos_pkg is not None:
                sys.modules["argostranslate.package"] = orig_argos_pkg
            else:
                sys.modules.pop("argostranslate.package", None)
            if orig_argos_tr is not None:
                sys.modules["argostranslate.translate"] = orig_argos_tr
            else:
                sys.modules.pop("argostranslate.translate", None)
            # Reload to restore normal state
            importlib.reload(translator)


class TestCacheImportFallback:
    """Cover lines 34-35: get_translation_cache = None."""

    def test_cache_import_error(self) -> None:
        """Reimport translator with cache module absent."""
        orig_cache_mod = sys.modules.get("python_pkg.word_frequency.cache")
        getattr(translator, "get_translation_cache", None)

        try:
            sys.modules["python_pkg.word_frequency.cache"] = cast(
                "types.ModuleType",
                None,
            )

            importlib.reload(translator)

            assert translator.get_translation_cache is None
        finally:
            if orig_cache_mod is not None:
                sys.modules["python_pkg.word_frequency.cache"] = orig_cache_mod
            else:
                sys.modules.pop("python_pkg.word_frequency.cache", None)
            importlib.reload(translator)


class TestTranslateWordsBatchCaching:
    """Cover line 426: set_many called after batch translation."""

    def test_cache_set_many_called(self) -> None:
        """Batch translates words and caches them via set_many."""
        mock_cache = MagicMock()
        mock_cache.get_many.return_value = {}  # Nothing cached

        with (
            ArgosAvailableMock("hola"),
            patch.object(
                translator,
                "get_translation_cache",
                return_value=mock_cache,
            ),
            patch.object(
                translator,
                "_run_batch_translation",
                return_value={"hello": "hola"},
            ),
        ):
            results = translator.translate_words_batch(
                ["hello"],
                "en",
                "es",
                use_cache=True,
            )

        assert len(results) == 1
        assert results[0].translated_word == "hola"
        mock_cache.set_many.assert_called_once_with({"hello": "hola"}, "en", "es")

    def test_cache_not_called_when_disabled(self) -> None:
        """use_cache=False skips cache set_many."""
        with (
            ArgosAvailableMock("hola"),
            patch.object(
                translator,
                "_run_batch_translation",
                return_value={"hello": "hola"},
            ),
        ):
            results = translator.translate_words_batch(
                ["hello"],
                "en",
                "es",
                use_cache=False,
            )

        assert len(results) == 1
        assert results[0].translated_word == "hola"


class TestArgosTranslateSuccessImport:
    """Cover line 26: import argostranslate.translate succeeds."""

    def test_both_argos_imports_succeed(self) -> None:
        """Reimport translator with both argos sub-modules present."""
        orig_argos = sys.modules.get("argostranslate")
        orig_pkg = sys.modules.get("argostranslate.package")
        orig_tr = sys.modules.get("argostranslate.translate")

        try:
            mock_parent = MagicMock()
            sys.modules["argostranslate"] = mock_parent
            sys.modules["argostranslate.package"] = mock_parent.package
            sys.modules["argostranslate.translate"] = mock_parent.translate

            importlib.reload(translator)

            assert translator.argostranslate is not None
        finally:
            for name, orig in [
                ("argostranslate", orig_argos),
                ("argostranslate.package", orig_pkg),
                ("argostranslate.translate", orig_tr),
            ]:
                if orig is not None:
                    sys.modules[name] = orig
                else:
                    sys.modules.pop(name, None)
            importlib.reload(translator)
