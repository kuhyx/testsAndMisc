import os

# Budget for the entire website (single file) in bytes
BUDGET = 14 * 1024  # 14 KiB

HERE = os.path.dirname(__file__)
SITE_FILE = os.path.join(HERE, 'index.html')


def test_site_file_exists():
    assert os.path.exists(SITE_FILE), f"Missing site file: {SITE_FILE}"


def test_site_size_under_budget():
    size = os.path.getsize(SITE_FILE)
    assert size <= BUDGET, f"Site size {size} bytes exceeds budget {BUDGET}"
