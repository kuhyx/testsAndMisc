#!/usr/bin/env python3
r"""Translator - translates words/text between languages.

This module provides translation capabilities using either:

1. Argos Translate (offline, requires large downloads)
2. deep-translator (online, uses Google Translate)

Usage::

    # Translate a single word
    python -m python_pkg.word_frequency.translator \\
        --text "hello" --from en --to es

    # Translate multiple words
    python -m python_pkg.word_frequency.translator \\
        --words hello world goodbye --from en --to pl

    # Translate words from a file (one word per line)
    python -m python_pkg.word_frequency.translator \\
        --words-file words.txt --from la --to en

    # List available languages
    python -m python_pkg.word_frequency.translator \\
        --list-languages

    # Output to file
    python -m python_pkg.word_frequency.translator \\
        --words-file vocab.txt --from pl --to en \\
        --output translations.txt

Dependencies (install one)::

    pip install deep-translator
    pip install argostranslate
"""

from __future__ import annotations

import argparse
import importlib
import logging
import os
from pathlib import Path
import subprocess
import sys
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from collections.abc import Sequence

try:
    import torch
except ImportError:
    torch = None  # type: ignore[assignment]

try:
    import argostranslate.package
    import argostranslate.translate
except ImportError:
    argostranslate = None  # type: ignore[assignment]

try:
    from deep_translator import GoogleTranslator
except ImportError:
    GoogleTranslator = None

try:
    import langdetect
except ImportError:
    langdetect = None  # type: ignore[assignment]

try:
    from python_pkg.word_frequency.cache import (
        get_translation_cache,
    )
except ImportError:
    get_translation_cache = None

logger = logging.getLogger(__name__)

_LANG_DETECT_SAMPLE_SIZE = 5000
_BATCH_SIZE = 100


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

    logger.info(
        "CUDA detected, initializing GPU acceleration..."
    )

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


def _check_argos() -> bool:
    """Check if argostranslate is available."""
    return argostranslate is not None


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
        return langdetect.detect(sample)  # type: ignore[no-any-return,union-attr]
    except langdetect.LangDetectException:  # type: ignore[attr-defined,union-attr]
        return None


class TranslationResult(NamedTuple):
    """Result of a translation."""

    source_word: str
    translated_word: str
    source_lang: str
    target_lang: str
    success: bool
    error: str | None = None


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


def _ensure_argos_installed() -> None:
    """Ensure argostranslate is installed, attempt installation if not.

    Raises:
        ImportError: If argos cannot be installed.
    """
    if _check_argos():
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
        msg = (
            "argostranslate installation succeeded but "
            "import failed"
        )
        raise ImportError(msg) from None


def _ensure_language_pair(from_lang: str, to_lang: str) -> None:
    """Ensure the language pair is available, download if needed.

    Args:
        from_lang: Source language code.
        to_lang: Target language code.

    Raises:
        ValueError: If language pair cannot be obtained.
    """
    installed_languages = (
        argostranslate.translate.get_installed_languages()
    )
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
        (
            p
            for p in available
            if p.from_code == from_lang and p.to_code == to_lang
        ),
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
        "  Downloading package (~50-100MB, "
        "this may take a minute)...",
    )
    download_path = pkg.download()
    logger.info("  Installing language pack...")
    argostranslate.package.install_from_path(download_path)
    logger.info(
        "Language pack %s -> %s installed.",
        from_lang,
        to_lang,
    )


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
            word, from_lang, to_lang,
        )
        # Cache the result
        if use_cache and get_translation_cache is not None:
            get_translation_cache().set(
                word, from_lang, to_lang, translated,
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

    gpu_status = (
        " (GPU)" if _check_cuda_available() else " (CPU)"
    )
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
                "  [%3d%%] Translating batch %d/%d "
                "(%d/%d words)...",
                pct,
                batch_idx + 1,
                total_batches,
                words_done,
                num_to_translate,
            )

            _, batch_translations = _translate_batch_worker(
                batch_words, from_lang, to_lang, batch_idx,
            )
            new_translations.update(batch_translations)

        logger.info("  Translation complete.")
    except Exception as e:
        msg = (
            f"Translation failed for "
            f"{from_lang} -> {to_lang}: {e}"
        )
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
            list(words), from_lang, to_lang,
        )

    # Find words that still need translation
    words_to_translate = [
        word for word in words
        if word.lower() not in cached_results
    ]

    # Translate uncached words using argos batch
    new_translations: dict[str, str] = {}
    if words_to_translate:
        new_translations = _run_batch_translation(
            words_to_translate, from_lang, to_lang,
        )

        # Cache new translations
        if use_cache and get_translation_cache is not None:
            get_translation_cache().set_many(
                new_translations, from_lang, to_lang,
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


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the translator CLI."""
    parser = argparse.ArgumentParser(
        description="Offline translator using Argos Translate.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    action_group = parser.add_mutually_exclusive_group()
    action_group.add_argument(
        "--list-languages",
        "-l",
        action="store_true",
        help="List installed languages",
    )
    action_group.add_argument(
        "--list-available",
        "-L",
        action="store_true",
        help="List available language packages for download",
    )
    action_group.add_argument(
        "--download",
        "-d",
        nargs="+",
        metavar="LANG",
        help=(
            "Download language packs "
            "(e.g., --download en es pl)"
        ),
    )

    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument(
        "--text",
        "-t",
        type=str,
        help="Single text/word to translate",
    )
    input_group.add_argument(
        "--words",
        "-w",
        nargs="+",
        help="Words to translate",
    )
    input_group.add_argument(
        "--words-file",
        "-W",
        type=str,
        help="File with words to translate (one per line)",
    )

    parser.add_argument(
        "--from",
        "-f",
        dest="from_lang",
        type=str,
        default="en",
        help="Source language code (default: en)",
    )
    parser.add_argument(
        "--to",
        "-T",
        dest="to_lang",
        type=str,
        default="en",
        help="Target language code (default: en)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Output file path",
    )

    return parser


def _handle_list_languages() -> int:
    """Handle --list-languages command."""
    langs = get_installed_languages()
    if not langs:
        sys.stdout.write("No languages installed.\n")
        sys.stdout.write(
            "Download some with: --download en es pl de fr\n",
        )
    else:
        sys.stdout.write("Installed languages:\n")
        for code, name in sorted(langs):
            sys.stdout.write(f"  {code}: {name}\n")
    return 0


def _handle_list_available() -> int:
    """Handle --list-available command."""
    packages = get_available_packages()
    if not packages:
        sys.stdout.write(
            "No packages available "
            "(check internet connection).\n",
        )
    else:
        sys.stdout.write("Available language packages:\n")
        for from_code, from_name, to_code, to_name in sorted(
            packages,
        ):
            sys.stdout.write(
                f"  {from_code} ({from_name})"
                f" -> {to_code} ({to_name})\n",
            )
    return 0


def _handle_download(lang_codes: list[str]) -> int:
    """Handle --download command."""
    download_results = download_languages(lang_codes)
    success_count = sum(
        1 for v in download_results.values() if v
    )
    sys.stdout.write(
        f"\nDownloaded {success_count}/"
        f"{len(download_results)} language pairs.\n",
    )
    return 0 if success_count > 0 else 1


def _collect_words(
    args: argparse.Namespace,
) -> list[str] | None:
    """Collect words from args. Returns None on error."""
    if args.text:
        return [args.text]
    if args.words:
        return args.words
    if args.words_file:
        try:
            content = read_file(args.words_file)
        except FileNotFoundError:
            sys.stderr.write(
                f"Error: File not found: {args.words_file}\n",
            )
            return None
        return [
            w.strip()
            for w in content.splitlines()
            if w.strip()
        ]
    return []


def _handle_translation(args: argparse.Namespace) -> int:
    """Handle the translation action."""
    try:
        results = translate_words_batch(
            args.words, args.from_lang, args.to_lang,
        )
    except ImportError:
        logger.exception("Translation import error")
        return 1

    output = format_translations(results)

    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        sys.stdout.write(
            f"Translations written to {args.output}\n",
        )
    else:
        sys.stdout.write(output + "\n")

    if any(not r.success for r in results):
        return 1

    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Main entry point for the translator.

    Args:
        argv: Command line arguments.

    Returns:
        Exit code.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    if not _check_argos():
        sys.stderr.write(
            "Error: argostranslate is not installed.\n"
            "Install it with: pip install argostranslate\n",
        )
        return 1

    if args.list_languages:
        return _handle_list_languages()
    if args.list_available:
        return _handle_list_available()
    if args.download:
        return _handle_download(args.download)

    words = _collect_words(args)
    if not words:
        if words is not None:
            parser.print_help()
        return 1

    args.words = words
    return _handle_translation(args)


if __name__ == "__main__":
    sys.exit(main())
