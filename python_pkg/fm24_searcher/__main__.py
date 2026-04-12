"""Entry point for FM24 Database Searcher.

Supports two modes:
- GUI (default): ``python -m python_pkg.fm24_searcher``
- CLI dump: ``python -m python_pkg.fm24_searcher --dump``
"""

from __future__ import annotations

import sys

from python_pkg.fm24_searcher.cli import run_dump
from python_pkg.fm24_searcher.gui import main


def _main() -> None:
    """Dispatch to GUI or CLI based on arguments."""
    if "--dump" in sys.argv:
        raise SystemExit(run_dump())
    main()


if __name__ == "__main__":
    _main()
