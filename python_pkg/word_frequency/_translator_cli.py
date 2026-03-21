"""Command-line interface for the translator module.

Provides argument parsing, CLI handlers, and the main entry point
for the offline translator using Argos Translate.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import TYPE_CHECKING

import python_pkg.word_frequency.translator as _trans

if TYPE_CHECKING:
    from collections.abc import Sequence

logger = __import__("logging").getLogger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the translator CLI."""
    parser = argparse.ArgumentParser(
        description="Offline translator using Argos Translate.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
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
        help=("Download language packs (e.g., --download en es pl)"),
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
    langs = _trans.get_installed_languages()
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
    packages = _trans.get_available_packages()
    if not packages:
        sys.stdout.write(
            "No packages available (check internet connection).\n",
        )
    else:
        sys.stdout.write("Available language packages:\n")
        for from_code, from_name, to_code, to_name in sorted(
            packages,
        ):
            sys.stdout.write(
                f"  {from_code} ({from_name}) -> {to_code} ({to_name})\n",
            )
    return 0


def _handle_download(lang_codes: list[str]) -> int:
    """Handle --download command."""
    download_results = _trans.download_languages(lang_codes)
    success_count = sum(1 for v in download_results.values() if v)
    sys.stdout.write(
        f"\nDownloaded {success_count}/{len(download_results)} language pairs.\n",
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
            content = _trans.read_file(args.words_file)
        except FileNotFoundError:
            sys.stderr.write(
                f"Error: File not found: {args.words_file}\n",
            )
            return None
        return [w.strip() for w in content.splitlines() if w.strip()]
    return []


def _handle_translation(args: argparse.Namespace) -> int:
    """Handle the translation action."""
    try:
        results = _trans.translate_words_batch(
            args.words,
            args.from_lang,
            args.to_lang,
        )
    except ImportError:
        logger.exception("Translation import error")
        return 1

    output = _trans.format_translations(results)

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

    if not _trans._check_argos():
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
