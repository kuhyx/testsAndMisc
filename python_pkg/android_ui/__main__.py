"""Module entry point for the Android UI driver.

Usage:
    PYTHONPATH=~/testsAndMisc python3 -m python_pkg.android_ui --help
"""

from __future__ import annotations

import sys

from python_pkg.android_ui.cli import main

if __name__ == "__main__":
    sys.exit(main())
