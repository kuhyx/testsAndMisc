"""Module entry point for the billsplit coverage gate.

Usage:
    PYTHONPATH=~/testsAndMisc python3 -m python_pkg.billsplit_coverage
"""

from __future__ import annotations

import sys

from python_pkg.billsplit_coverage.checker import main

if __name__ == "__main__":
    sys.exit(main())
