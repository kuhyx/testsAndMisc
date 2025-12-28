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
import sys
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from collections.abc import Sequence

# Lazy imports for translation backends (may not be installed)
_argos_available: bool | None = None
_deep_translator_available: bool | None = None
_langdetect_available: bool | None = None


def _check_argos() -> bool:
    """Check if argostranslate is available."""
    global _argos_available
    if _argos_available is None:
        try:
            import argostranslate.package  # noqa: F401
            import argostranslate.translate  # noqa: F401

            _argos_available = True
        except ImportError:
            _argos_available = False
    return _argos_available


def _check_deep_translator() -> bool:
    """Check if deep-translator is available."""
    global _deep_translator_available
    if _deep_translator_available is None:
        try:
            from deep_translator import GoogleTranslator  # noqa: F401

            _deep_translator_available = True
        except ImportError:
            _deep_translator_available = False
    return _deep_translator_available


def _check_langdetect() -> bool:
    """Check if langdetect is available."""
    global _langdetect_available
    if _langdetect_available is None:
        try:
            import langdetect  # noqa: F401

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
    print("Updating package index...")  # noqa: T201
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
                    print(f"Downloading {from_code} -> {to_code}...")  # noqa: T201
                    argostranslate.package.install_from_path(pkg.download())
                    results[key] = True
                    print(f"  ✓ Installed {from_code} -> {to_code}")  # noqa: T201
                except Exception as e:  # noqa: BLE001
                    results[key] = False
                    print(f"  ✗ Failed {from_code} -> {to_code}: {e}")  # noqa: T201
            else:
                # Package not available
                results[key] = False

    return results


def translate_word(
    word: str,
    from_lang: str,
    to_lang: str,
) -> TranslationResult:
    """Translate a single word.

    Uses argostranslate if available (offline), otherwise falls back to
    deep-translator (Google Translate, online).

    Args:
        word: The word to translate.
        from_lang: Source language code (e.g., 'en', 'pl', 'la').
        to_lang: Target language code.

    Returns:
        TranslationResult with the translation.
    """
    # Try argostranslate first (offline)
    if _check_argos():
        import argostranslate.translate

        try:
            translated = argostranslate.translate.translate(word, from_lang, to_lang)
            return TranslationResult(
                source_word=word,
                translated_word=translated,
                source_lang=from_lang,
                target_lang=to_lang,
                success=True,
            )
        except Exception as e:  # noqa: BLE001
            # Fall through to try deep-translator
            argos_error = str(e)
    else:
        argos_error = None

    # Try deep-translator (online via Google Translate)
    if _check_deep_translator():
        from deep_translator import GoogleTranslator

        try:
            translator = GoogleTranslator(source=from_lang, target=to_lang)
            translated = translator.translate(word)
            return TranslationResult(
                source_word=word,
                translated_word=translated or "",
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

    # Neither backend available
    error_msg = "No translation backend available. Install: pip install deep-translator"
    if argos_error:
        error_msg = f"argostranslate error: {argos_error}"
    return TranslationResult(
        source_word=word,
        translated_word="",
        source_lang=from_lang,
        target_lang=to_lang,
        success=False,
        error=error_msg,
    )


def translate_words(
    words: Sequence[str],
    from_lang: str,
    to_lang: str,
) -> list[TranslationResult]:
    """Translate multiple words.

    Args:
        words: List of words to translate.
        from_lang: Source language code.
        to_lang: Target language code.

    Returns:
        List of TranslationResult for each word.
    """
    return [translate_word(word, from_lang, to_lang) for word in words]


def translate_words_batch(
    words: Sequence[str],
    from_lang: str,
    to_lang: str,
) -> list[TranslationResult]:
    """Translate multiple words, attempting batch translation for efficiency.

    For better results with context, this joins words and translates together,
    then splits. Falls back to word-by-word if batch fails.

    Args:
        words: List of words to translate.
        from_lang: Source language code.
        to_lang: Target language code.

    Returns:
        List of TranslationResult for each word.
    """
    if not words:
        return []

    # For single words or small batches, just translate individually
    if len(words) <= 3:
        return translate_words(words, from_lang, to_lang)

    # Try batch translation by joining with newlines
    if not _check_argos():
        return translate_words(words, from_lang, to_lang)

    import argostranslate.translate

    try:
        # Join words with newlines for batch translation
        batch_text = "\n".join(words)
        translated_batch = argostranslate.translate.translate(
            batch_text, from_lang, to_lang
        )
        translated_words = translated_batch.split("\n")

        # If we got the same number of translations, use them
        if len(translated_words) == len(words):
            return [
                TranslationResult(
                    source_word=word,
                    translated_word=trans.strip(),
                    source_lang=from_lang,
                    target_lang=to_lang,
                    success=True,
                )
                for word, trans in zip(words, translated_words, strict=True)
            ]
    except Exception:  # noqa: BLE001, S110
        pass

    # Fall back to individual translation
    return translate_words(words, from_lang, to_lang)


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
            lines.append(f"{r.source_word:<{max_source}}  {r.translated_word:<{max_trans}}")
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
        print(  # noqa: T201
            "Error: argostranslate is not installed.\n"
            "Install it with: pip install argostranslate",
            file=sys.stderr,
        )
        return 1

    # Handle list-languages
    if args.list_languages:
        langs = get_installed_languages()
        if not langs:
            print("No languages installed.")  # noqa: T201
            print("Download some with: --download en es pl de fr")  # noqa: T201
        else:
            print("Installed languages:")  # noqa: T201
            for code, name in sorted(langs):
                print(f"  {code}: {name}")  # noqa: T201
        return 0

    # Handle list-available
    if args.list_available:
        packages = get_available_packages()
        if not packages:
            print("No packages available (check internet connection).")  # noqa: T201
        else:
            print("Available language packages:")  # noqa: T201
            for from_code, from_name, to_code, to_name in sorted(packages):
                print(f"  {from_code} ({from_name}) -> {to_code} ({to_name})")  # noqa: T201
        return 0

    # Handle download
    if args.download:
        results = download_languages(args.download)
        success_count = sum(1 for v in results.values() if v)
        print(f"\nDownloaded {success_count}/{len(results)} language pairs.")  # noqa: T201
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
            print(f"Error: File not found: {args.words_file}", file=sys.stderr)  # noqa: T201
            return 1

    if not words:
        parser.print_help()
        return 1

    # Translate
    results = translate_words_batch(words, args.from_lang, args.to_lang)
    output = format_translations(results)

    # Output
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"Translations written to {args.output}")  # noqa: T201
    else:
        print(output)  # noqa: T201

    # Return error if any translation failed
    if any(not r.success for r in results):
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
