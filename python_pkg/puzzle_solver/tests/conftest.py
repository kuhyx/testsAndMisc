"""Mock cv2/numpy if not installed before puzzle_solver tests."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

sys.modules.setdefault("cv2", MagicMock())
sys.modules.setdefault("numpy", MagicMock())
