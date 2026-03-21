"""Pytest conftest for anki_decks tests.

Ensures the geo_data package is importable by adding python_pkg/ to sys.path.
"""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
