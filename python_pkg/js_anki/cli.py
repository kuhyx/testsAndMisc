"""CLI: verify every example in Node, then write the Anki .apkg."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from python_pkg.js_anki.deck import build_package
from python_pkg.js_anki.models import load_all
from python_pkg.js_anki.verify import VerificationError, verify

DEFAULT_OUT = Path(__file__).parent / "build" / "js_methods.apkg"


def build_parser() -> argparse.ArgumentParser:
    """Argument parser with a single `build` subcommand."""
    parser = argparse.ArgumentParser(prog="js_anki", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    build = sub.add_parser("build", help="verify examples and write the .apkg")
    build.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI; non-zero exit if any example fails verification."""
    args = build_parser().parse_args(argv)
    entries = load_all()
    try:
        verify(entries)
    except VerificationError as exc:
        sys.stderr.write(f"verification FAILED:\n{exc}\n")
        return 1
    package, count = build_package(entries)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    package.write_to_file(str(args.out))
    sys.stdout.write(
        f"verified {len(entries)} examples; wrote {count} cards to {args.out}\n"
    )
    return 0
