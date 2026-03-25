"""Tests for uncovered branches in python_pkg.puzzle_solver.parse_image."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import numpy as np

from python_pkg.puzzle_solver.parse_image import (
    _assign_teleporter_and_kl_groups,
    _build_output,
    _classify_all,
    _detect_portal_side,
    _has_interior_feature,
)

CV2 = "python_pkg.puzzle_solver.parse_image.cv2"
NP = "python_pkg.puzzle_solver.parse_image.np"


# ── _classify_all ────────────────────────────────────────────────────


class TestClassifyAllPart2:
    @patch("python_pkg.puzzle_solver.parse_image._classify_one")
    def test_loop_body_populates_classified(self, mock_classify: MagicMock) -> None:
        mock_classify.return_value = ("normal", {})
        gray = MagicMock()
        grid_map = {(0, 0): (10, 20, 30, 40)}
        result = _classify_all(gray, grid_map)
        assert (0, 0) in result
        d = result[(0, 0)]
        assert d["pos"] == [0, 0]
        assert d["type"] == "normal"
        assert d["pixel_center"] == [10 + 30 // 2, 20 + 40 // 2]
        assert d["pixel_bbox"] == [10, 20, 30, 40]

    @patch("python_pkg.puzzle_solver.parse_image._classify_one")
    def test_multiple_entries(self, mock_classify: MagicMock) -> None:
        mock_classify.side_effect = [
            ("player", {}),
            ("goal", {}),
        ]
        gray = MagicMock()
        grid_map = {
            (0, 0): (0, 0, 20, 20),
            (1, 1): (50, 50, 20, 20),
        }
        result = _classify_all(gray, grid_map)
        assert len(result) == 2
        assert result[(0, 0)]["type"] == "player"
        assert result[(1, 1)]["type"] == "goal"

    @patch("python_pkg.puzzle_solver.parse_image._classify_one")
    def test_extra_dict_merged(self, mock_classify: MagicMock) -> None:
        mock_classify.return_value = ("portal", {"side": "left"})
        gray = MagicMock()
        grid_map = {(2, 3): (100, 100, 40, 40)}
        result = _classify_all(gray, grid_map)
        assert result[(2, 3)]["side"] == "left"


# ── _detect_portal_side ──────────────────────────────────────────────


class TestDetectPortalSide:
    def test_too_small_height(self) -> None:
        interior = MagicMock()
        interior.shape = (3, 20)
        assert _detect_portal_side(interior) is None

    def test_too_small_width(self) -> None:
        interior = MagicMock()
        interior.shape = (20, 3)
        assert _detect_portal_side(interior) is None

    @patch(NP)
    def test_clear_best_side_left(self, mock_np: MagicMock) -> None:
        interior = MagicMock()
        interior.shape = (30, 30)
        # thirds_w=10, thirds_h=10
        # Regions: left gets high value, others low
        mock_np.mean.side_effect = [
            50.0,  # left
            5.0,  # right
            5.0,  # up
            5.0,  # down
        ]
        result = _detect_portal_side(interior)
        assert result == "left"

    @patch(NP)
    def test_clear_best_side_right(self, mock_np: MagicMock) -> None:
        interior = MagicMock()
        interior.shape = (30, 30)
        mock_np.mean.side_effect = [
            5.0,  # left
            50.0,  # right
            5.0,  # up
            5.0,  # down
        ]
        result = _detect_portal_side(interior)
        assert result == "right"

    @patch(NP)
    def test_clear_best_side_up(self, mock_np: MagicMock) -> None:
        interior = MagicMock()
        interior.shape = (30, 30)
        mock_np.mean.side_effect = [
            5.0,  # left
            5.0,  # right
            50.0,  # up
            5.0,  # down
        ]
        result = _detect_portal_side(interior)
        assert result == "up"

    @patch(NP)
    def test_clear_best_side_down(self, mock_np: MagicMock) -> None:
        interior = MagicMock()
        interior.shape = (30, 30)
        mock_np.mean.side_effect = [
            5.0,  # left
            5.0,  # right
            5.0,  # up
            50.0,  # down
        ]
        result = _detect_portal_side(interior)
        assert result == "down"

    @patch(NP)
    def test_no_clear_winner_returns_none(self, mock_np: MagicMock) -> None:
        interior = MagicMock()
        interior.shape = (30, 30)
        # All regions similar → best is not > max(opp*2.5, 8)
        mock_np.mean.side_effect = [
            6.0,  # left
            5.0,  # right (opposite of left)
            5.0,  # up
            5.0,  # down
        ]
        # best = left (6.0), opp = right (5.0)
        # condition: 6.0 > max(5.0*2.5, 8) = max(12.5, 8) = 12.5 → False
        result = _detect_portal_side(interior)
        assert result is None

    @patch(NP)
    def test_best_above_threshold_8(self, mock_np: MagicMock) -> None:
        interior = MagicMock()
        interior.shape = (30, 30)
        # best > max(opp*2.5, 8) where opp is very small
        mock_np.mean.side_effect = [
            10.0,  # left
            1.0,  # right (opposite of left)
            1.0,  # up
            1.0,  # down
        ]
        # best = left (10.0), opp = right (1.0)
        # condition: 10.0 > max(1.0*2.5, 8) = max(2.5, 8) = 8 → True
        result = _detect_portal_side(interior)
        assert result == "left"


# ── _has_interior_feature ────────────────────────────────────────────


class TestHasInteriorFeature:
    @patch(NP)
    @patch(CV2)
    def test_feature_present(self, mock_cv2: MagicMock, mock_np: MagicMock) -> None:
        interior = MagicMock()
        interior.size = 100
        bw = np.zeros((10, 10), dtype=np.uint8)
        mock_cv2.threshold.return_value = (None, bw)
        # total_white > interior.size * 0.06 = 6
        mock_np.sum.return_value = 10
        assert _has_interior_feature(interior) is True

    @patch(NP)
    @patch(CV2)
    def test_no_feature(self, mock_cv2: MagicMock, mock_np: MagicMock) -> None:
        interior = MagicMock()
        interior.size = 100
        bw = np.zeros((10, 10), dtype=np.uint8)
        mock_cv2.threshold.return_value = (None, bw)
        mock_np.sum.return_value = 3
        assert _has_interior_feature(interior) is False


# ── _assign_teleporter_and_kl_groups ─────────────────────────────────


class TestAssignTeleporterAndKlGroups:
    def test_pair_by_matching_antenna_sides(self) -> None:
        classified: dict[tuple[int, int], dict[str, Any]] = {
            (0, 0): {"type": "teleporter", "antenna_sides": ["up"]},
            (1, 1): {"type": "teleporter", "antenna_sides": ["up"]},
        }
        _assign_teleporter_and_kl_groups(classified)
        assert classified[(0, 0)]["group"] == classified[(1, 1)]["group"]

    def test_skip_already_used_in_inner_loop(self) -> None:
        classified: dict[tuple[int, int], dict[str, Any]] = {
            (0, 0): {"type": "teleporter", "antenna_sides": ["up"]},
            (0, 1): {"type": "teleporter", "antenna_sides": ["up"]},
            (1, 0): {"type": "teleporter", "antenna_sides": ["down"]},
            (1, 1): {"type": "teleporter", "antenna_sides": ["down"]},
        }
        _assign_teleporter_and_kl_groups(classified)
        # (0,0) pairs with (0,1), (1,0) pairs with (1,1)
        assert classified[(0, 0)]["group"] == classified[(0, 1)]["group"]
        assert classified[(1, 0)]["group"] == classified[(1, 1)]["group"]
        assert classified[(0, 0)]["group"] != classified[(1, 0)]["group"]

    def test_p1_already_used_skip(self) -> None:
        # 3 teleporters with same sides; first two pair, third is unpaired
        classified: dict[tuple[int, int], dict[str, Any]] = {
            (0, 0): {"type": "teleporter", "antenna_sides": ["up"]},
            (0, 1): {"type": "teleporter", "antenna_sides": ["up"]},
            (0, 2): {"type": "teleporter", "antenna_sides": ["up"]},
        }
        _assign_teleporter_and_kl_groups(classified)
        # (0,0) pairs with (0,1) by antenna match
        # (0,2) remains unpaired by antenna, but gets sequential pairing? No,
        # only 1 unpaired, can't pair sequentially (need pairs of 2)
        assert classified[(0, 0)]["group"] == classified[(0, 1)]["group"]
        # (0,2) ends up with no group since unpaired count is 1 (odd)
        assert "group" not in classified[(0, 2)]

    def test_unpaired_teleporters_sequential(self) -> None:
        # Teleporters with non-matching antenna → no antenna pairing → sequential
        classified: dict[tuple[int, int], dict[str, Any]] = {
            (0, 0): {"type": "teleporter", "antenna_sides": ["up"]},
            (0, 1): {"type": "teleporter", "antenna_sides": ["down"]},
        }
        _assign_teleporter_and_kl_groups(classified)
        # Neither antenna-pairs with the other, so both go to sequential
        assert classified[(0, 0)]["group"] == classified[(0, 1)]["group"]

    def test_key_lock_pairing(self) -> None:
        classified: dict[tuple[int, int], dict[str, Any]] = {
            (0, 0): {"type": "key_or_lock"},
            (0, 1): {"type": "key_or_lock"},
        }
        _assign_teleporter_and_kl_groups(classified)
        assert classified[(0, 0)]["type"] == "key"
        assert classified[(0, 0)]["lock_id"] == 1
        assert classified[(0, 1)]["type"] == "lock"
        assert classified[(0, 1)]["lock_id"] == 1

    def test_key_lock_odd_one_out(self) -> None:
        classified: dict[tuple[int, int], dict[str, Any]] = {
            (0, 0): {"type": "key_or_lock"},
            (0, 1): {"type": "key_or_lock"},
            (0, 2): {"type": "key_or_lock"},
        }
        _assign_teleporter_and_kl_groups(classified)
        # First two pair, third becomes unknown
        assert classified[(0, 0)]["type"] == "key"
        assert classified[(0, 1)]["type"] == "lock"
        assert classified[(0, 2)]["type"] == "unknown"

    def test_no_teleporters_no_kl(self) -> None:
        classified: dict[tuple[int, int], dict[str, Any]] = {
            (0, 0): {"type": "normal"},
        }
        _assign_teleporter_and_kl_groups(classified)
        assert classified[(0, 0)]["type"] == "normal"

    def test_multiple_key_lock_pairs(self) -> None:
        classified: dict[tuple[int, int], dict[str, Any]] = {
            (0, 0): {"type": "key_or_lock"},
            (0, 1): {"type": "key_or_lock"},
            (1, 0): {"type": "key_or_lock"},
            (1, 1): {"type": "key_or_lock"},
        }
        _assign_teleporter_and_kl_groups(classified)
        assert classified[(0, 0)]["lock_id"] == 1
        assert classified[(0, 1)]["lock_id"] == 1
        assert classified[(1, 0)]["lock_id"] == 2
        assert classified[(1, 1)]["lock_id"] == 2


# ── _build_output ────────────────────────────────────────────────────


class TestBuildOutput:
    def test_normal_square(self) -> None:
        classified: dict[tuple[int, int], dict[str, Any]] = {
            (0, 0): {
                "pos": [0, 0],
                "type": "normal",
                "pixel_center": [10, 10],
                "pixel_bbox": [0, 0, 20, 20],
            },
        }
        result = _build_output(classified)
        assert len(result["squares"]) == 1
        sq = result["squares"][0]
        assert sq["pos"] == [0, 0]
        assert sq["type"] == "normal"
        assert sq["_pixel_center"] == [10, 10]
        assert sq["_pixel_bbox"] == [0, 0, 20, 20]
        assert result["notes"] == []

    def test_portal_with_side(self) -> None:
        classified: dict[tuple[int, int], dict[str, Any]] = {
            (0, 0): {
                "pos": [0, 0],
                "type": "portal",
                "side": "left",
                "pixel_center": [10, 10],
                "pixel_bbox": [0, 0, 20, 20],
            },
        }
        result = _build_output(classified)
        assert result["squares"][0]["side"] == "left"

    def test_teleporter_with_group(self) -> None:
        classified: dict[tuple[int, int], dict[str, Any]] = {
            (0, 0): {
                "pos": [0, 0],
                "type": "teleporter",
                "group": 1,
                "pixel_center": [10, 10],
                "pixel_bbox": [0, 0, 20, 20],
            },
        }
        result = _build_output(classified)
        assert result["squares"][0]["group"] == 1

    def test_key_with_lock_id(self) -> None:
        classified: dict[tuple[int, int], dict[str, Any]] = {
            (0, 0): {
                "pos": [0, 0],
                "type": "key",
                "lock_id": 1,
                "pixel_center": [10, 10],
                "pixel_bbox": [0, 0, 20, 20],
            },
        }
        result = _build_output(classified)
        assert result["squares"][0]["lock_id"] == 1

    def test_unknown_generates_note(self) -> None:
        classified: dict[tuple[int, int], dict[str, Any]] = {
            (0, 0): {
                "pos": [0, 0],
                "type": "unknown",
                "fill_ratio": 0.2,
                "pixel_center": [10, 10],
                "pixel_bbox": [0, 0, 20, 20],
            },
        }
        result = _build_output(classified)
        assert len(result["notes"]) == 1
        assert "unknown" in result["notes"][0]
        assert "fill=0.2" in result["notes"][0]

    def test_unknown_no_fill_ratio(self) -> None:
        classified: dict[tuple[int, int], dict[str, Any]] = {
            (0, 0): {
                "pos": [0, 0],
                "type": "unknown",
                "pixel_center": [10, 10],
                "pixel_bbox": [0, 0, 20, 20],
            },
        }
        result = _build_output(classified)
        assert "fill=?" in result["notes"][0]

    def test_sorted_output(self) -> None:
        classified: dict[tuple[int, int], dict[str, Any]] = {
            (1, 0): {
                "pos": [1, 0],
                "type": "normal",
                "pixel_center": [10, 10],
                "pixel_bbox": [0, 0, 20, 20],
            },
            (0, 0): {
                "pos": [0, 0],
                "type": "normal",
                "pixel_center": [5, 5],
                "pixel_bbox": [0, 0, 10, 10],
            },
        }
        result = _build_output(classified)
        assert result["squares"][0]["pos"] == [0, 0]
        assert result["squares"][1]["pos"] == [1, 0]
