"""Tests to ensure website stays within size budget."""

from pathlib import Path

# Budget for the entire website (single file) in bytes
BUDGET = 14 * 1024  # 14 KiB

HERE = Path(__file__).parent
SITE_FILE = HERE / "index.html"


def test_site_file_exists() -> None:
    """Verify the main site HTML file exists."""
    assert SITE_FILE.exists(), f"Missing site file: {SITE_FILE}"


def test_site_size_under_budget() -> None:
    """Verify site size is under the defined budget."""
    size = SITE_FILE.stat().st_size
    assert size <= BUDGET, f"Site size {size} bytes exceeds budget {BUDGET}"
