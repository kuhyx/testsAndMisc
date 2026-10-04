"""Module entry point for the JS-methods Anki deck builder.

Usage:
    PYTHONPATH=~/src/testsAndMisc python3 -m python_pkg.js_anki build
"""

from __future__ import annotations

import sys

from python_pkg.js_anki.cli import main

if __name__ == "__main__":
    sys.exit(main())
