"""Tests for draw_debug in python_pkg.puzzle_solver.parse_image."""

from __future__ import annotations

import sys
from typing import Any
from unittest.mock import MagicMock, patch

# Install mock modules before any parse_image imports
sys.modules.setdefault("cv2", MagicMock())
sys.modules.setdefault("numpy", MagicMock())

from python_pkg.puzzle_solver.parse_image import (
    _assign_teleporter_and_kl_groups,
    draw_debug,
)

CV2 = "python_pkg.puzzle_solver.parse_image.cv2"


# ── draw_debug ───────────────────────────────────────────────────────


class TestDrawDebug:
    @patch(CV2)
    def test_image_not_found_returns_early(self, mock_cv2: MagicMock) -> None:
        mock_cv2.imread.return_value = None
        draw_debug("nofile.png", {"squares": []}, "out.png")
        mock_cv2.imwrite.assert_not_called()

    @patch(CV2)
    def test_draws_normal_square(self, mock_cv2: MagicMock) -> None:
        mock_img = MagicMock()
        mock_cv2.imread.return_value = mock_img
        puzzle: dict[str, Any] = {
            "squares": [
                {
                    "type": "normal",
                    "_pixel_bbox": [10, 20, 30, 40],
                },
            ],
        }
        draw_debug("img.png", puzzle, "out.png")
        mock_cv2.rectangle.assert_called_once()
        mock_cv2.putText.assert_called_once()
        mock_cv2.imwrite.assert_called_once_with("out.png", mock_img)

    @patch(CV2)
    def test_draws_portal_with_arrows(self, mock_cv2: MagicMock) -> None:
        mock_img = MagicMock()
        mock_cv2.imread.return_value = mock_img
        puzzle: dict[str, Any] = {
            "squares": [
                {
                    "type": "portal",
                    "side": "left",
                    "_pixel_bbox": [10, 20, 30, 40],
                },
            ],
        }
        draw_debug("img.png", puzzle, "out.png")
        # label should be "<" for left
        args = mock_cv2.putText.call_args
        assert args[0][1] == "<"

    @patch(CV2)
    def test_draws_portal_right_arrow(self, mock_cv2: MagicMock) -> None:
        mock_img = MagicMock()
        mock_cv2.imread.return_value = mock_img
        puzzle: dict[str, Any] = {
            "squares": [
                {
                    "type": "portal",
                    "side": "right",
                    "_pixel_bbox": [10, 20, 30, 40],
                },
            ],
        }
        draw_debug("img.png", puzzle, "out.png")
        args = mock_cv2.putText.call_args
        assert args[0][1] == ">"

    @patch(CV2)
    def test_draws_portal_up_arrow(self, mock_cv2: MagicMock) -> None:
        mock_img = MagicMock()
        mock_cv2.imread.return_value = mock_img
        puzzle: dict[str, Any] = {
            "squares": [
                {
                    "type": "portal",
                    "side": "up",
                    "_pixel_bbox": [10, 20, 30, 40],
                },
            ],
        }
        draw_debug("img.png", puzzle, "out.png")
        args = mock_cv2.putText.call_args
        assert args[0][1] == "^"

    @patch(CV2)
    def test_draws_portal_down_arrow(self, mock_cv2: MagicMock) -> None:
        mock_img = MagicMock()
        mock_cv2.imread.return_value = mock_img
        puzzle: dict[str, Any] = {
            "squares": [
                {
                    "type": "portal",
                    "side": "down",
                    "_pixel_bbox": [10, 20, 30, 40],
                },
            ],
        }
        draw_debug("img.png", puzzle, "out.png")
        args = mock_cv2.putText.call_args
        assert args[0][1] == "v"

    @patch(CV2)
    def test_portal_no_side_uses_o(self, mock_cv2: MagicMock) -> None:
        mock_img = MagicMock()
        mock_cv2.imread.return_value = mock_img
        puzzle: dict[str, Any] = {
            "squares": [
                {
                    "type": "portal",
                    "_pixel_bbox": [10, 20, 30, 40],
                },
            ],
        }
        draw_debug("img.png", puzzle, "out.png")
        args = mock_cv2.putText.call_args
        assert args[0][1] == "O"

    @patch(CV2)
    def test_unknown_type_fallback_colour(self, mock_cv2: MagicMock) -> None:
        mock_img = MagicMock()
        mock_cv2.imread.return_value = mock_img
        puzzle: dict[str, Any] = {
            "squares": [
                {
                    "type": "nonexistent_type",
                    "_pixel_bbox": [10, 20, 30, 40],
                },
            ],
        }
        draw_debug("img.png", puzzle, "out.png")
        # Should use fallback colour (128, 128, 128)
        rect_args = mock_cv2.rectangle.call_args
        assert rect_args[0][3] == (128, 128, 128)

    @patch(CV2)
    def test_multiple_squares(self, mock_cv2: MagicMock) -> None:
        mock_img = MagicMock()
        mock_cv2.imread.return_value = mock_img
        puzzle: dict[str, Any] = {
            "squares": [
                {"type": "player", "_pixel_bbox": [0, 0, 10, 10]},
                {"type": "goal", "_pixel_bbox": [20, 20, 10, 10]},
            ],
        }
        draw_debug("img.png", puzzle, "out.png")
        assert mock_cv2.rectangle.call_count == 2
        assert mock_cv2.putText.call_count == 2


# ── _assign_teleporter_and_kl_groups: inner p2-in-used branch ────────


class TestTeleporterInnerUsedSkip:
    def test_inner_loop_skips_already_used_p2(self) -> None:
        """Line 338: inner continue when p2 already in used set.

        Teleporters ordered so that after A pairs with C (skipping B),
        B's inner loop encounters the already-used C before finding D.
        """
        classified: dict[tuple[int, int], dict[str, Any]] = {
            (0, 0): {"type": "teleporter", "antenna_sides": ["up"]},
            (1, 0): {"type": "teleporter", "antenna_sides": ["down"]},
            (2, 0): {"type": "teleporter", "antenna_sides": ["up"]},
            (3, 0): {"type": "teleporter", "antenna_sides": ["down"]},
        }
        _assign_teleporter_and_kl_groups(classified)
        # (0,0) pairs with (2,0) by antenna match (both "up")
        assert classified[(0, 0)]["group"] == classified[(2, 0)]["group"]
        # (1,0) pairs with (3,0) by antenna match (both "down"),
        # after skipping already-used (2,0) in the inner loop
        assert classified[(1, 0)]["group"] == classified[(3, 0)]["group"]
        assert classified[(0, 0)]["group"] != classified[(1, 0)]["group"]
