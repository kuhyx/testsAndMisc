#!/usr/bin/env python3
"""Translator - translates words/text between languages.

This module provides translation capabilities using either:
1. Argos Translate (offline, requires large downloads) - preferred if installed
2. deep-translator (online, uses Google Translate) - lightweight fallback

Usage:
    # Translate a single word
    python -m python_pkg.word_frequency.translator --text "hello" --from en --to es

    # Translate multiple words
    python -m python_pkg.word_frequency.translator --words hello world goodbye --from en --to pl

    # Translate words from a file (one word per line)
    python -m python_pkg.word_frequency.translator --words-file words.txt --from la --to en

    # List available languages
    python -m python_pkg.word_frequency.translator --list-languages

    # Output to file
    python -m python_pkg.word_frequency.translator --words-file vocab.txt --from pl --to en --output translations.txt

Dependencies (install one):
    pip install deep-translator    # Lightweight, uses Google Translate (online)
    pip install argostranslate     # Offline translation (requires ~3GB downloads)
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from collections.abc import Sequence

# Lazy imports for translation backends (may not be installed)
_argos_available: bool | None = None
_deep_translator_available: bool | None = None
_langdetect_available: bool | None = None
_gpu_initialized: bool = False
_gpu_available: bool | None = None


def _check_cuda_available() -> bool:
    """Check if CUDA is available for GPU acceleration."""
    global _gpu_available
    if _gpu_available is None:
        try:
            import torch

            _gpu_available = torch.cuda.is_available()
        except ImportError:
            _gpu_available = False
    return _gpu_available


def _init_gpu_if_available() -> None:
    """Initialize GPU for argostranslate if CUDA is available.

    Raises:
        RuntimeError: If CUDA is available but GPU initialization fails.
    """
    global _gpu_initialized
    if _gpu_initialized:
        return

    if not _check_cuda_available():
        _gpu_initialized = True
        return

    import sys

    print("CUDA detected, initializing GPU acceleration...", file=sys.stderr)

    try:
        import torch

        # Force CTranslate2 to use CUDA
        device_count = torch.cuda.device_count()
        if device_count == 0:
            raise RuntimeError("CUDA reports available but no GPU devices found")

        device_name = torch.cuda.get_device_name(0)
        print(f"  Using GPU: {device_name}", file=sys.stderr)

        # Set environment variable to force GPU usage in argos
        import os

        os.environ["CT2_CUDA_ALLOW_FP16"] = "1"
        os.environ["CT2_USE_EXPERIMENTAL_PACKED_GEMM"] = "1"

        _gpu_initialized = True
        print("  GPU acceleration enabled.", file=sys.stderr)

    except Exception as e:
        raise RuntimeError(
            f"CUDA is available but GPU initialization failed: {e}\n"
            f"This may be due to incompatible CUDA version or driver issues.\n"
            f"To disable GPU and use CPU only, set environment variable: CT2_FORCE_CPU=1"
        ) from e


def _check_argos() -> bool:
    """Check if argostranslate is available."""
    global _argos_available
    if _argos_available is None:
        try:
            import argostranslate.package
            import argostranslate.translate

            _ = (argostranslate.package, argostranslate.translate)
            _argos_available = True
        except ImportError:
            _argos_available = False
    return _argos_available


def _check_deep_translator() -> bool:
    """Check if deep-translator is available."""
    global _deep_translator_available
    if _deep_translator_available is None:
        try:
            from deep_translator import GoogleTranslator

            _ = GoogleTranslator
            _deep_translator_available = True
        except ImportError:
            _deep_translator_available = False
    return _deep_translator_available


def _check_langdetect() -> bool:
    """Check if langdetect is available."""
    global _langdetect_available
    if _langdetect_available is None:
        try:
            import langdetect

            _ = langdetect
            _langdetect_available = True
        except ImportError:
            _langdetect_available = False
    return _langdetect_available


def detect_language(text: str) -> str | None:
    """Detect the language of a text.

    Args:
        text: The text to analyze.

    Returns:
        ISO 639-1 language code (e.g., 'en', 'la', 'pl') or None if detection fails.
    """
    if not _check_langdetect():
        return None

    import langdetect

    try:
        # Use a sample of the text for detection (faster and more reliable)
        sample = text[:5000] if len(text) > 5000 else text
        return langdetect.detect(sample)  # type: ignore[no-any-return]
    except langdetect.LangDetectException:  # type: ignore[attr-defined]
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

    import argostranslate.translate

    languages = argostranslate.translate.get_installed_languages()
    return [(lang.code, lang.name) for lang in languages]


def get_available_packages() -> list[tuple[str, str, str, str]]:
    """Get list of available language packages for download.

    Returns:
        List of (from_code, from_name, to_code, to_name) tuples.
    """
    if not _check_argos():
        return []

    import argostranslate.package

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

    import argostranslate.package

    results: dict[str, bool] = {}

    # Update package index
    print("Updating package index...")
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
                    print(f"Downloading {from_code} -> {to_code}...")
                    argostranslate.package.install_from_path(pkg.download())
                    results[key] = True
                    print(f"  ✓ Installed {from_code} -> {to_code}")
                except Exception as e:  # noqa: BLE001
                    results[key] = False
                    print(f"  ✗ Failed {from_code} -> {to_code}: {e}")
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

    import subprocess
    import sys

    print("argostranslate not found. Attempting to install...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "argostranslate"],
            check=True,
            capture_output=True,
        )
        # Reset the check flag and verify
        global _argos_available
        _argos_available = None
        if not _check_argos():
            raise ImportError("argostranslate installation succeeded but import failed")
        print("argostranslate installed successfully.")
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode() if e.stderr else str(e)
        raise ImportError(
            f"argostranslate is required for offline translation.\n\n"
            f"Install manually with one of:\n"
            f"  pip install argostranslate          # In a virtualenv\n"
            f"  pipx install argostranslate         # System-wide via pipx\n"
            f"  pacman -S python-argostranslate     # Arch Linux (if available)\n\n"
            f"Original error: {error_msg}"
        ) from e


def _ensure_language_pair(from_lang: str, to_lang: str) -> None:
    """Ensure the language pair is available, download if needed.

    Args:
        from_lang: Source language code.
        to_lang: Target language code.

    Raises:
        ValueError: If language pair cannot be obtained.
    """
    import argostranslate.package
    import argostranslate.translate

    # Check if already installed
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
    import sys

    print(
        f"Downloading language pack: {from_lang} -> {to_lang}...",
        file=sys.stderr,
    )
    print("  Fetching package index...", file=sys.stderr)
    argostranslate.package.update_package_index()
    available = argostranslate.package.get_available_packages()

    pkg = next(
        (p for p in available if p.from_code == from_lang and p.to_code == to_lang),
        None,
    )

    if pkg is None:
        raise ValueError(
            f"No language pack available for {from_lang} -> {to_lang}. "
            f"Available pairs can be listed with --list-languages."
        )

    print(
        "  Downloading package (~50-100MB, this may take a minute)...",
        file=sys.stderr,
    )
    download_path = pkg.download()
    print("  Installing language pack...", file=sys.stderr)
    argostranslate.package.install_from_path(download_path)
    print(
        f"Language pack {from_lang} -> {to_lang} installed.",
        file=sys.stderr,
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
    if use_cache:
        try:
            from python_pkg.word_frequency.cache import get_translation_cache

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
        except ImportError:
            pass  # Cache not available

    # Ensure argos is installed (will raise if it can't be)
    _ensure_argos_installed()

    import argostranslate.translate

    try:
        translated = argostranslate.translate.translate(word, from_lang, to_lang)
        # Cache the result
        if use_cache:
            try:
                from python_pkg.word_frequency.cache import get_translation_cache

                get_translation_cache().set(word, from_lang, to_lang, translated)
            except ImportError:
                pass
        return TranslationResult(
            source_word=word,
            translated_word=translated,
            source_lang=from_lang,
            target_lang=to_lang,
            success=True,
        )
    except Exception as e:  # noqa: BLE001
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
    import argostranslate.translate

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

    # Ensure argos is installed (will raise if it can't be)
    _ensure_argos_installed()

    # Initialize GPU if available (will raise if CUDA available but fails)
    _init_gpu_if_available()

    # Ensure language pair is available
    _ensure_language_pair(from_lang, to_lang)

    # Check cache for already-translated words
    cached_results: dict[str, str] = {}
    words_to_translate: list[str] = []

    if use_cache:
        try:
            from python_pkg.word_frequency.cache import get_translation_cache

            cache = get_translation_cache()
            cached_results = cache.get_many(list(words), from_lang, to_lang)
        except ImportError:
            pass

    # Find words that still need translation
    for word in words:
        if word.lower() not in cached_results:
            words_to_translate.append(word)

    # Translate uncached words using argos batch
    new_translations: dict[str, str] = {}
    if words_to_translate:
        import sys

        num_to_translate = len(words_to_translate)

        # Check if GPU is being used
        gpu_status = " (GPU)" if _gpu_available else " (CPU)"
        print(
            f"Translating {num_to_translate} words from {from_lang} to {to_lang}{gpu_status}...",
            file=sys.stderr,
            flush=True,
        )

        try:
            # Split into batches - larger batches are faster but show progress less often
            BATCH_SIZE = 100
            batches: list[list[str]] = []
            for i in range(0, num_to_translate, BATCH_SIZE):
                batches.append(words_to_translate[i : i + BATCH_SIZE])

            total_batches = len(batches)

            # Sequential translation with progress
            # (argostranslate is not thread-safe - uses global model)
            for batch_idx, batch_words in enumerate(batches):
                words_done = (batch_idx + 1) * BATCH_SIZE
                words_done = min(words_done, num_to_translate)
                pct = int(words_done / num_to_translate * 100)

                print(
                    f"  [{pct:3d}%] Translating batch {batch_idx + 1}/{total_batches} "
                    f"({words_done}/{num_to_translate} words)...",
                    file=sys.stderr,
                    flush=True,
                )

                _, batch_translations = _translate_batch_worker(
                    batch_words, from_lang, to_lang, batch_idx
                )
                new_translations.update(batch_translations)

            print("  Translation complete.", file=sys.stderr, flush=True)
        except Exception as e:
            raise RuntimeError(
                f"Translation failed for {from_lang} -> {to_lang}: {e}"
            ) from e

        # Cache new translations
        if use_cache and new_translations:
            try:
                from python_pkg.word_frequency.cache import get_translation_cache

                get_translation_cache().set_many(new_translations, from_lang, to_lang)
            except ImportError:
                pass

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


def main(argv: Sequence[str] | None = None) -> int:
    """Main entry point for the translator.

    Args:
        argv: Command line arguments.

    Returns:
        Exit code.
    """
    parser = argparse.ArgumentParser(
        description="Offline translator using Argos Translate.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Actions
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
        help="Download language packs (e.g., --download en es pl)",
    )

    # Input
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

    # Language options
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

    # Output
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Output file path",
    )

    args = parser.parse_args(argv)

    # Check if argostranslate is available
    if not _check_argos():
        print(
            "Error: argostranslate is not installed.\n"
            "Install it with: pip install argostranslate",
            file=sys.stderr,
        )
        return 1

    # Handle list-languages
    if args.list_languages:
        langs = get_installed_languages()
        if not langs:
            print("No languages installed.")
            print("Download some with: --download en es pl de fr")
        else:
            print("Installed languages:")
            for code, name in sorted(langs):
                print(f"  {code}: {name}")
        return 0

    # Handle list-available
    if args.list_available:
        packages = get_available_packages()
        if not packages:
            print("No packages available (check internet connection).")
        else:
            print("Available language packages:")
            for from_code, from_name, to_code, to_name in sorted(packages):
                print(f"  {from_code} ({from_name}) -> {to_code} ({to_name})")
        return 0

    # Handle download
    if args.download:
        download_results = download_languages(args.download)
        success_count = sum(1 for v in download_results.values() if v)
        print(f"\nDownloaded {success_count}/{len(download_results)} language pairs.")
        return 0 if success_count > 0 else 1

    # Handle translation
    words: list[str] = []
    if args.text:
        words = [args.text]
    elif args.words:
        words = args.words
    elif args.words_file:
        try:
            content = read_file(args.words_file)
            words = [w.strip() for w in content.splitlines() if w.strip()]
        except FileNotFoundError:
            print(f"Error: File not found: {args.words_file}", file=sys.stderr)
            return 1

    if not words:
        parser.print_help()
        return 1

    # Translate
    try:
        results = translate_words_batch(words, args.from_lang, args.to_lang)
    except ImportError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    output = format_translations(results)

    # Output
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"Translations written to {args.output}")
    else:
        print(output)

    # Return error if any translation failed
    if any(not r.success for r in results):
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
