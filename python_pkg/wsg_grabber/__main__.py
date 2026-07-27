"""Module entry point.

Usage:
    PYTHONPATH=~/testsAndMisc python3 -m python_pkg.wsg_grabber --help
"""

from __future__ import annotations

import sys

from python_pkg.wsg_grabber.cli import main

if __name__ == "__main__":
    sys.exit(main())
