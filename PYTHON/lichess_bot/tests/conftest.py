import os
from pathlib import Path
import sys

# Add repository root to sys.path so 'import PYTHON.*' works when running
# pytest with a subdirectory as rootdir.
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def pytest_ignore_collect(collection_path: Path, config):
    """Ignore per-game blunder test files; keep only the unified one.

    This lets us keep historical files in the repo without collecting them.
    """
    basename = collection_path.name
    if basename.startswith("test_blunders_") and basename != "test_blunders_all.py":
        return True
    return False
