"""Coverage gate for the ``billsplit/`` Flutter app.

``flutter test --coverage`` reports success while leaving whole files untouched,
so this package re-reads the lcov report it produces and fails unless every
``lib/`` file is present *and* fully covered. It lives here rather than beside
the app because every Python file in this repository belongs under
``python_pkg/``; the app itself holds only Dart.

Usage:
    PYTHONPATH=~/testsAndMisc python3 -m python_pkg.billsplit_coverage
"""

from __future__ import annotations
