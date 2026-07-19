"""Module entry point for the shared app-icon generator.

Usage:
    PYTHONPATH=~/testsAndMisc python3 -m python_pkg.app_icons --help
"""

from __future__ import annotations

import sys

from python_pkg.app_icons.cli import main

if __name__ == "__main__":
    sys.exit(main())
