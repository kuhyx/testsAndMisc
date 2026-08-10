"""Module entry point for the offline Arch Wiki RAG corpus builder.

Usage:
    PYTHONPATH=~/testsAndMisc python3 -m python_pkg.archwiki_rag --help
"""

from __future__ import annotations

import sys

from python_pkg.archwiki_rag.cli import main

if __name__ == "__main__":
    sys.exit(main())
