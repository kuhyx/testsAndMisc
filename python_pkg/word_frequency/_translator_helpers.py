"""Helper utilities for the translator module.

Contains GPU initialization, backend availability checks, language detection,
translation result types, formatting, and Argos Translate setup functions.
"""

from __future__ import annotations

import importlib
import logging
import os
from pathlib import Path
import subprocess
import sys
from typing import NamedTuple

try:
    import torch
except ImportError:
    torch = None

try:
    import argostranslate.package
    import argostranslate.translate
except ImportError:
    argostranslate = None

try:
    from deep_translator import GoogleTranslator
except ImportError:
    GoogleTranslator = None

try:
    import langdetect
except ImportError:
    langdetect = None

logger = logging.getLogger(__name__)

_LANG_DETECT_SAMPLE_SIZE = 5000


class _TranslatorState:
    """Holds module-level state for lazy-initialized backends."""

    gpu_initialized: bool = False


def _check_cuda_available() -> bool:
    """Check if CUDA is available for GPU acceleration."""
    return torch is not None and torch.cuda.is_available()


def _validate_gpu_device() -> str:
    """Validate GPU device availability and return device name.

    Raises:
        RuntimeError: If no GPU devices are found.
    """
    device_count = torch.cuda.device_count()
    if device_count == 0:
        msg = "CUDA reports available but no GPU devices found"
        raise RuntimeError(msg)
    return torch.cuda.get_device_name(0)


def _init_gpu_if_available() -> None:
    """Initialize GPU for argostranslate if CUDA is available.

    Raises:
        RuntimeError: If CUDA is available but GPU init fails.
    """
    if _TranslatorState.gpu_initialized:
        return

    if not _check_cuda_available():
        _TranslatorState.gpu_initialized = True
        return

    logger.info("CUDA detected, initializing GPU acceleration...")

    try:
        device_name = _validate_gpu_device()
        logger.info("  Using GPU: %s", device_name)

        os.environ["CT2_CUDA_ALLOW_FP16"] = "1"
        os.environ["CT2_USE_EXPERIMENTAL_PACKED_GEMM"] = "1"

        _TranslatorState.gpu_initialized = True
        logger.info("  GPU acceleration enabled.")

    except Exception as e:
        msg = (
            f"CUDA is available but GPU initialization failed: "
            f"{e}\nThis may be due to incompatible CUDA "
            "version or driver issues.\n"
            "To disable GPU and use CPU only, set "
            "environment variable: CT2_FORCE_CPU=1"
        )
        raise RuntimeError(msg) from e


def _check_deep_translator() -> bool:
    """Check if deep-translator is available."""
    return GoogleTranslator is not None


def _check_langdetect() -> bool:
    """Check if langdetect is available."""
    return langdetect is not None


def detect_language(text: str) -> str | None:
    """Detect the language of a text.

    Args:
        text: The text to analyze.

    Returns:
        ISO 639-1 language code (e.g., 'en', 'la', 'pl') or None if detection fails.
    """
    if not _check_langdetect():
        return None

    try:
        sample = (
            text[:_LANG_DETECT_SAMPLE_SIZE]
            if len(text) > _LANG_DETECT_SAMPLE_SIZE
            else text
        )
        return langdetect.detect(sample)
    except langdetect.LangDetectException:
        return None


class TranslationResult(NamedTuple):
    """Result of a translation."""

    source_word: str
    translated_word: str
    source_lang: str
    target_lang: str
    success: bool
    error: str | None = None


def format_translations(
    results: list[TranslationResult],
    *,
    show_errors: bool = True,
) -> str:
    """Format translation results as a table.

    Args:
        results: List of TranslationResult to format.
        show_errors: If True, show error messages for failed translations.

    Returns:
        Formatted string with translations.
    """
    if not results:
        return "No translations."

    lines: list[str] = []

    # Find max widths
    max_source = max(len(r.source_word) for r in results)
    max_source = max(max_source, 6)  # "Source" header

    successful_lengths = [len(r.translated_word) for r in results if r.success]
    max_trans = max(successful_lengths) if successful_lengths else 0
    max_trans = max(max_trans, 11)  # "Translation" header minimum

    # Header
    from_lang = results[0].source_lang
    to_lang = results[0].target_lang
    lines.append(f"Translation: {from_lang} -> {to_lang}")
    lines.append("")
    lines.append(f"{'Source':<{max_source}}  {'Translation':<{max_trans}}")
    lines.append("-" * (max_source + max_trans + 2))

    # Data
    for r in results:
        if r.success:
            lines.append(
                f"{r.source_word:<{max_source}}  {r.translated_word:<{max_trans}}"
            )
        elif show_errors:
            error_msg = f"[Error: {r.error}]" if r.error else "[Failed]"
            lines.append(f"{r.source_word:<{max_source}}  {error_msg}")

    return "\n".join(lines)


def read_file(filepath: str | Path) -> str:
    """Read text content from a file."""
    return Path(filepath).read_text(encoding="utf-8")


def _ensure_argos_installed() -> None:
    """Ensure argostranslate is installed, attempt installation if not.

    Raises:
        ImportError: If argos cannot be installed.
    """
    if argostranslate is not None:
        return

    logger.info("argostranslate not found. Attempting to install...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "argostranslate"],
            check=True,
            capture_output=True,
        )
        # Attempt runtime re-import
        importlib.import_module("argostranslate.package")
        importlib.import_module("argostranslate.translate")
        logger.info("argostranslate installed successfully.")
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode() if e.stderr else str(e)
        msg = (
            "argostranslate is required for offline "
            "translation.\n\n"
            "Install manually with one of:\n"
            "  pip install argostranslate"
            "          # In a virtualenv\n"
            "  pipx install argostranslate"
            "         # System-wide via pipx\n"
            "  pacman -S python-argostranslate"
            "     # Arch Linux (if available)\n\n"
            f"Original error: {error_msg}"
        )
        raise ImportError(msg) from e
    except ImportError:
        msg = "argostranslate installation succeeded but import failed"
        raise ImportError(msg) from None


def _ensure_language_pair(from_lang: str, to_lang: str) -> None:
    """Ensure the language pair is available, download if needed.

    Args:
        from_lang: Source language code.
        to_lang: Target language code.

    Raises:
        ValueError: If language pair cannot be obtained.
    """
    installed_languages = argostranslate.translate.get_installed_languages()
    from_lang_obj = None
    to_lang_obj = None

    for lang in installed_languages:
        if lang.code == from_lang:
            from_lang_obj = lang
        if lang.code == to_lang:
            to_lang_obj = lang

    if from_lang_obj and to_lang_obj:
        # Check if translation is available
        translation = from_lang_obj.get_translation(to_lang_obj)
        if translation:
            return  # Already available

    # Need to download
    logger.info(
        "Downloading language pack: %s -> %s...",
        from_lang,
        to_lang,
    )
    logger.info("  Fetching package index...")
    argostranslate.package.update_package_index()
    available = argostranslate.package.get_available_packages()

    pkg = next(
        (p for p in available if p.from_code == from_lang and p.to_code == to_lang),
        None,
    )

    if pkg is None:
        msg = (
            f"No language pack available for "
            f"{from_lang} -> {to_lang}. "
            "Available pairs can be listed with "
            "--list-languages."
        )
        raise ValueError(msg)

    logger.info(
        "  Downloading package (~50-100MB, this may take a minute)...",
    )
    download_path = pkg.download()
    logger.info("  Installing language pack...")
    argostranslate.package.install_from_path(download_path)
    logger.info(
        "Language pack %s -> %s installed.",
        from_lang,
        to_lang,
    )
