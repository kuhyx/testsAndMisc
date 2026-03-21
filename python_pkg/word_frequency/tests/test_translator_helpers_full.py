"""Tests for word_frequency._translator_helpers module."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from pathlib import Path

import python_pkg.word_frequency._translator_helpers as _helpers
from python_pkg.word_frequency._translator_helpers import (
    TranslationResult,
    _check_cuda_available,
    _check_deep_translator,
    _check_langdetect,
    _ensure_argos_installed,
    _ensure_language_pair,
    _init_gpu_if_available,
    _TranslatorState,
    _validate_gpu_device,
    detect_language,
    format_translations,
    read_file,
)


class TestCheckCudaAvailable:
    """Tests for _check_cuda_available."""

    def test_no_torch(self) -> None:
        with patch.object(_helpers, "torch", None):
            assert _check_cuda_available() is False

    def test_torch_no_cuda(self) -> None:
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = False
        with patch.object(_helpers, "torch", mock_torch):
            assert _check_cuda_available() is False

    def test_cuda_available(self) -> None:
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = True
        with patch.object(_helpers, "torch", mock_torch):
            assert _check_cuda_available() is True


class TestValidateGpuDevice:
    """Tests for _validate_gpu_device."""

    def test_no_devices(self) -> None:
        mock_torch = MagicMock()
        mock_torch.cuda.device_count.return_value = 0
        with (
            patch.object(_helpers, "torch", mock_torch),
            pytest.raises(RuntimeError, match="no GPU devices"),
        ):
            _validate_gpu_device()

    def test_has_device(self) -> None:
        mock_torch = MagicMock()
        mock_torch.cuda.device_count.return_value = 1
        mock_torch.cuda.get_device_name.return_value = "GTX 3090"
        with patch.object(_helpers, "torch", mock_torch):
            name = _validate_gpu_device()
        assert name == "GTX 3090"


class TestInitGpuIfAvailable:
    """Tests for _init_gpu_if_available."""

    def test_already_initialized(self) -> None:
        _TranslatorState.gpu_initialized = True
        _init_gpu_if_available()
        _TranslatorState.gpu_initialized = False

    def test_no_cuda(self) -> None:
        _TranslatorState.gpu_initialized = False
        with patch.object(_helpers, "torch", None):
            _init_gpu_if_available()
        assert _TranslatorState.gpu_initialized is True
        _TranslatorState.gpu_initialized = False

    def test_cuda_success(self) -> None:
        _TranslatorState.gpu_initialized = False
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.device_count.return_value = 1
        mock_torch.cuda.get_device_name.return_value = "GPU"
        with patch.object(_helpers, "torch", mock_torch):
            _init_gpu_if_available()
        assert _TranslatorState.gpu_initialized is True
        _TranslatorState.gpu_initialized = False

    def test_cuda_init_fails(self) -> None:
        _TranslatorState.gpu_initialized = False
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.device_count.side_effect = RuntimeError("GPU fail")
        with (
            patch.object(_helpers, "torch", mock_torch),
            pytest.raises(RuntimeError, match="GPU initialization failed"),
        ):
            _init_gpu_if_available()
        _TranslatorState.gpu_initialized = False


class TestCheckBackends:
    """Tests for backend availability checks."""

    def test_deep_translator_none(self) -> None:
        with patch.object(_helpers, "GoogleTranslator", None):
            assert _check_deep_translator() is False

    def test_deep_translator_available(self) -> None:
        with patch.object(_helpers, "GoogleTranslator", MagicMock()):
            assert _check_deep_translator() is True

    def test_langdetect_none(self) -> None:
        with patch.object(_helpers, "langdetect", None):
            assert _check_langdetect() is False

    def test_langdetect_available(self) -> None:
        with patch.object(_helpers, "langdetect", MagicMock()):
            assert _check_langdetect() is True


class TestDetectLanguage:
    """Tests for detect_language."""

    def test_no_langdetect(self) -> None:
        with patch.object(_helpers, "langdetect", None):
            assert detect_language("hello world") is None

    def test_detects_language(self) -> None:
        mock_ld = MagicMock()
        mock_ld.detect.return_value = "en"
        with patch.object(_helpers, "langdetect", mock_ld):
            result = detect_language("hello world")
        assert result == "en"

    def test_detection_exception(self) -> None:
        mock_ld = MagicMock()
        exc_class = type("LangDetectException", (Exception,), {})
        mock_ld.LangDetectException = exc_class
        mock_ld.detect.side_effect = exc_class("error")
        with patch.object(_helpers, "langdetect", mock_ld):
            result = detect_language("x")
        assert result is None

    def test_long_text_truncated(self) -> None:
        mock_ld = MagicMock()
        mock_ld.detect.return_value = "en"
        long_text = "hello " * 2000
        with patch.object(_helpers, "langdetect", mock_ld):
            detect_language(long_text)
        call_arg = mock_ld.detect.call_args[0][0]
        assert len(call_arg) <= 5000


class TestEnsureArgosInstalled:
    """Tests for _ensure_argos_installed."""

    def test_already_available(self) -> None:
        with patch.object(_helpers, "argostranslate", MagicMock()):
            _ensure_argos_installed()

    def test_not_available_installs(self) -> None:
        with (
            patch.object(_helpers, "argostranslate", None),
            patch.object(_helpers.subprocess, "run") as mock_run,
            patch.object(_helpers.importlib, "import_module"),
        ):
            mock_run.return_value = MagicMock(returncode=0)
            _ensure_argos_installed()
        mock_run.assert_called_once()

    def test_install_fails(self) -> None:
        import subprocess

        with (
            patch.object(_helpers, "argostranslate", None),
            patch.object(
                _helpers.subprocess,
                "run",
                side_effect=subprocess.CalledProcessError(
                    1, "pip", stderr=b"install error"
                ),
            ),
            pytest.raises(ImportError, match="argostranslate is required"),
        ):
            _ensure_argos_installed()

    def test_import_fails_after_install(self) -> None:
        with (
            patch.object(_helpers, "argostranslate", None),
            patch.object(_helpers.subprocess, "run") as mock_run,
            patch.object(
                _helpers.importlib,
                "import_module",
                side_effect=ImportError("import fail"),
            ),
        ):
            mock_run.return_value = MagicMock(returncode=0)
            with pytest.raises(ImportError, match="import failed"):
                _ensure_argos_installed()


class TestEnsureLanguagePair:
    """Tests for _ensure_language_pair."""

    def test_pair_already_installed(self) -> None:
        mock_from = MagicMock()
        mock_from.code = "en"
        mock_from.get_translation.return_value = MagicMock()
        mock_to = MagicMock()
        mock_to.code = "es"
        mock_argos = MagicMock()
        mock_argos.translate.get_installed_languages.return_value = [
            mock_from,
            mock_to,
        ]
        with patch.object(_helpers, "argostranslate", mock_argos):
            _ensure_language_pair("en", "es")

    def test_pair_needs_download(self) -> None:
        mock_from = MagicMock()
        mock_from.code = "en"
        mock_from.get_translation.return_value = None
        mock_to = MagicMock()
        mock_to.code = "es"
        mock_pkg = MagicMock()
        mock_pkg.from_code = "en"
        mock_pkg.to_code = "es"
        mock_pkg.download.return_value = "/tmp/pkg.argosmodel"
        mock_argos = MagicMock()
        mock_argos.translate.get_installed_languages.return_value = [
            mock_from,
            mock_to,
        ]
        mock_argos.package.get_available_packages.return_value = [mock_pkg]
        with patch.object(_helpers, "argostranslate", mock_argos):
            _ensure_language_pair("en", "es")
        mock_argos.package.install_from_path.assert_called_once()

    def test_pair_not_available(self) -> None:
        mock_argos = MagicMock()
        mock_argos.translate.get_installed_languages.return_value = []
        mock_argos.package.get_available_packages.return_value = []
        with (
            patch.object(_helpers, "argostranslate", mock_argos),
            pytest.raises(ValueError, match="No language pack available"),
        ):
            _ensure_language_pair("en", "xx")

    def test_pair_not_installed_no_from_lang(self) -> None:
        mock_to = MagicMock()
        mock_to.code = "es"
        mock_pkg = MagicMock()
        mock_pkg.from_code = "en"
        mock_pkg.to_code = "es"
        mock_pkg.download.return_value = "/tmp/pkg"
        mock_argos = MagicMock()
        mock_argos.translate.get_installed_languages.return_value = [mock_to]
        mock_argos.package.get_available_packages.return_value = [mock_pkg]
        with patch.object(_helpers, "argostranslate", mock_argos):
            _ensure_language_pair("en", "es")


class TestFormatTranslations:
    """Test edge cases for format_translations."""

    def test_failed_with_no_error(self) -> None:
        results = [
            TranslationResult("xyz", "", "en", "es", False),
        ]
        output = format_translations(results)
        assert "[Failed]" in output

    def test_all_failed_max_trans(self) -> None:
        results = [
            TranslationResult("xyz", "", "en", "es", False, "err"),
        ]
        output = format_translations(results)
        assert "Translation" in output


class TestReadFile:
    """Tests for read_file."""

    def test_reads(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("hello", encoding="utf-8")
        assert read_file(f) == "hello"

    def test_string_path(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("hello", encoding="utf-8")
        assert read_file(str(f)) == "hello"


class TestArgosImportReload:
    """Test import-time argostranslate.translate coverage via reload."""

    def test_argos_import_success_reload(self) -> None:
        """Cover line 24 (import argostranslate.translate) via reload."""
        mock_pkg = MagicMock()
        mock_trans = MagicMock()
        mock_parent = MagicMock()
        mock_parent.package = mock_pkg
        mock_parent.translate = mock_trans

        with patch.dict(
            "sys.modules",
            {
                "argostranslate": mock_parent,
                "argostranslate.package": mock_pkg,
                "argostranslate.translate": mock_trans,
            },
        ):
            importlib.reload(_helpers)
        # Restore original module state
        importlib.reload(_helpers)
