"""Command-line entry point for the offline Arch Wiki RAG corpus.

Usage:
    PYTHONPATH=~/testsAndMisc python -m python_pkg.archwiki_rag sync
    PYTHONPATH=~/testsAndMisc python -m python_pkg.archwiki_rag sync --reindex
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from python_pkg.archwiki_rag import reindex as reindex_mod
from python_pkg.archwiki_rag.constants import (
    DEFAULT_STORE_DIR,
    DOCUMENTS_SUBDIR,
    WIKI_HTML_DIR,
)
from python_pkg.archwiki_rag.sync import sync_pages


def _emit(message: str) -> None:
    """Write a line to stdout.

    Parameters:
    message (str): Line to write, without a trailing newline.
    """
    sys.stdout.write(f"{message}\n")


def build_parser() -> argparse.ArgumentParser:
    """Construct the argument parser.

    Returns:
    argparse.ArgumentParser: Parser with the ``sync`` subcommand.
    """
    parser = argparse.ArgumentParser(
        prog="python -m python_pkg.archwiki_rag",
        description="Convert the offline ArchWiki dump into a knowledge-rag corpus.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    sync_parser = subparsers.add_parser(
        "sync",
        help="convert the HTML dump to Markdown, optionally reindexing after",
    )
    sync_parser.add_argument(
        "--source",
        type=Path,
        default=WIKI_HTML_DIR,
        help=f"offline HTML tree (default: {WIKI_HTML_DIR})",
    )
    sync_parser.add_argument(
        "--store",
        type=Path,
        default=DEFAULT_STORE_DIR,
        help=f"knowledge-rag store to populate (default: {DEFAULT_STORE_DIR})",
    )
    sync_parser.add_argument(
        "--reindex",
        action="store_true",
        help="reindex afterwards when any page changed",
    )
    sync_parser.add_argument(
        "--ignore-load",
        action="store_true",
        help="reindex even when the machine is already under load",
    )
    return parser


def run_sync(args: argparse.Namespace) -> int:
    """Execute the ``sync`` subcommand.

    Parameters:
    args (argparse.Namespace): Parsed arguments.

    Returns:
    int: Process exit status.
    """
    source: Path = args.source
    if not source.is_dir():
        _emit(f"error: no HTML dump at {source} (is arch-wiki-docs installed?)")
        return 1

    result = sync_pages(source, args.store / DOCUMENTS_SUBDIR)
    _emit(
        f"converted {result.converted}, changed {result.changed}, "
        f"skipped {result.skipped}",
    )

    if not args.reindex:
        return 0
    if result.changed == 0:
        _emit("nothing changed; skipping reindex")
        return 0

    reason = reindex_mod.blocking_reason(args.store, ignore_load=args.ignore_load)
    if reason is not None:
        _emit(f"deferring reindex: {reason}")
        return 0

    _emit("reindexing...")
    return reindex_mod.run_reindex(args.store)


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and dispatch.

    Parameters:
    argv (list[str] | None): Argument vector, defaulting to ``sys.argv[1:]``.

    Returns:
    int: Process exit status.
    """
    args = build_parser().parse_args(argv)
    return run_sync(args)
