"""Tests for python_pkg.puzzle_solver.parse_image module."""

from __future__ import annotations

from unittest.mock import MagicMock, mock_open, patch

import pytest

from python_pkg.puzzle_solver.parse_image import (
    _classify_by_fill,
    _classify_interior_feature,
    _classify_one,
    _cluster_values,
    _detect_antenna,
    _is_ring_pattern,
    _merge_overlapping,
    _snap_to_grid,
    parse_image,
    save_puzzle,
)

# Get the actual cv2/np references used inside the module
CV2 = "python_pkg.puzzle_solver.parse_image.cv2"
NP = "python_pkg.puzzle_solver.parse_image.np"


# ── parse_image ──────────────────────────────────────────────────────


class TestParseImage:
    @patch(CV2)
    def test_file_not_found(self, mock_cv2: MagicMock) -> None:
        mock_cv2.imread.return_value = None
        with pytest.raises(FileNotFoundError, match="Cannot load image"):
            parse_image("nonexistent.png")

    @patch(NP)
    @patch(CV2)
    def test_successful_parse(self, mock_cv2: MagicMock, mock_np: MagicMock) -> None:
        mock_img = MagicMock()
        mock_cv2.imread.return_value = mock_img
        mock_gray = MagicMock()
        mock_cv2.cvtColor.return_value = mock_gray
        mock_binary = MagicMock()
        mock_cv2.threshold.return_value = (None, mock_binary)
        mock_np.ones.return_value = MagicMock()
        mock_cv2.morphologyEx.return_value = mock_binary
        # No contours → empty grid
        mock_cv2.findContours.return_value = ([], None)

        result = parse_image("test.png")
        assert "squares" in result
        assert "notes" in result


# ── save_puzzle ──────────────────────────────────────────────────────


class TestSavePuzzle:
    def test_save(self) -> None:
        m = mock_open()
        with patch("pathlib.Path.open", m):
            save_puzzle({"squares": [], "notes": []}, "out.json")
        m.assert_called_once()


# ── _detect_square_candidates ────────────────────────────────────────


class TestDetectSquareCandidates:
    @patch(NP)
    @patch(CV2)
    def test_filters_by_area_and_aspect(
        self, mock_cv2: MagicMock, mock_np: MagicMock
    ) -> None:
        from python_pkg.puzzle_solver.parse_image import _detect_square_candidates

        mock_binary = MagicMock()
        mock_cv2.threshold.return_value = (None, mock_binary)
        mock_np.ones.return_value = MagicMock()
        mock_cv2.morphologyEx.return_value = mock_binary

        cnt_good = MagicMock()
        cnt_small = MagicMock()
        cnt_big = MagicMock()
        cnt_thin = MagicMock()

        mock_cv2.findContours.return_value = (
            [cnt_good, cnt_small, cnt_big, cnt_thin],
            None,
        )
        mock_cv2.boundingRect.side_effect = [
            (10, 10, 10, 10),  # good: area=100
            (0, 0, 2, 5),  # small: area=10 < 80
            (0, 0, 200, 100),  # big: area=20000 > 12000
            (0, 0, 100, 1),  # thin: area=100 >= 80, aspect=0.01 < 0.45
        ]

        gray = MagicMock()
        result = _detect_square_candidates(gray, 55)
        assert len(result) == 1
        assert result[0] == (10, 10, 10, 10)


# ── _merge_overlapping ──────────────────────────────────────────────


class TestMergeOverlapping:
    def test_empty(self) -> None:
        assert _merge_overlapping([]) == []

    def test_no_overlap(self) -> None:
        candidates = [(0, 0, 10, 10), (100, 100, 10, 10)]
        result = _merge_overlapping(candidates)
        assert len(result) == 2

    def test_overlapping_merged(self) -> None:
        candidates = [(10, 10, 20, 20), (12, 12, 20, 20)]
        result = _merge_overlapping(candidates)
        assert len(result) == 1

    def test_used_flag_skips(self) -> None:
        candidates = [(10, 10, 20, 20), (11, 11, 20, 20), (200, 200, 10, 10)]
        result = _merge_overlapping(candidates)
        assert len(result) == 2

    def test_inner_used_j_skip(self) -> None:
        # Three overlapping boxes in chain: A overlaps B, B overlaps C.
        # After A merges with B (used[B]=True), when processing C's inner loop,
        # B is already used so `used[j]: continue` is hit.
        # Sorted by area desc: all same size, so order stays.
        # A at (10,10,20,20), B at (12,12,20,20), C at (14,14,20,20)
        # A merges with B and C (all close centres).
        # When i=1(B), used[1]=True, skip. When i=2(C), used[2]=True, skip.
        # We need i outer loop to encounter used[j] in inner loop.
        # Actually: A(largest), B, C sorted desc by area.
        # i=0(A): j=1(B) overlap -> merge, j=2(C) overlap -> merge. All used.
        # That covers used[j] in inner loop because j=2 is checked only when
        # it hasn't overlapped yet.
        # To get the `used[j]: continue` branch we need:
        # 3 items where first two merge, and the third is separate but in inner
        # loop sees the already-used second item.
        # A(big) at (0,0,30,30) area=900
        # B(med) at (2,2,20,20) area=400 - close to A, merges
        # C(small) at (100,100,10,10) area=100 - far away
        # Sorted desc: A, B, C
        # i=0(A): j=1(B) overlap→merge used[1]=True. j=2(C) no overlap.
        # i=1(B): used[1]→skip (outer).
        # i=2(C): inner loop j=3..end → no inner iterations.
        # Hmm, the `used[j]` branch in inner loop is at line 99-100.
        # Need: outer i processes some item, inner j finds used[j]=True.
        # 4 items: A overlaps B. C has inner loop that finds B (already used).
        candidates = [
            (0, 0, 30, 30),  # A: area=900
            (2, 2, 28, 28),  # B: area=784, close to A → merges
            (200, 200, 20, 20),  # C: area=400, separate
            (3, 3, 10, 10),  # D: area=100, close to A/B
        ]
        # Sorted desc by area: A(900), B(784), C(400), D(100)
        # i=0(A): j=1(B) overlap → merge, used[1]=True.
        #         j=2(C) no overlap. j=3(D) overlap → merge, used[3]=True.
        # i=1(B): used[1] → skip (outer continue).
        # i=2(C): j=3(D) used[3] → `continue` (inner) ← THIS IS LINE 100!
        result = _merge_overlapping(candidates)
        assert len(result) == 2


# ── _cluster_values ──────────────────────────────────────────────────


class TestClusterValues:
    def test_empty(self) -> None:
        assert _cluster_values([], 10) == []

    @patch(NP)
    def test_single_cluster(self, mock_np: MagicMock) -> None:
        mock_np.mean.side_effect = lambda c: sum(c) / len(c)
        result = _cluster_values([10, 12, 14], 5)
        assert len(result) == 1

    @patch(NP)
    def test_multiple_clusters(self, mock_np: MagicMock) -> None:
        mock_np.mean.side_effect = lambda c: sum(c) / len(c)
        result = _cluster_values([10, 12, 50, 52], 5)
        assert len(result) == 2


# ── _snap_to_grid ────────────────────────────────────────────────────


class TestSnapToGrid:
    @patch(NP)
    def test_basic_grid(self, mock_np: MagicMock) -> None:
        mock_np.median.return_value = 50
        mock_np.mean.side_effect = lambda c: sum(c) / len(c)

        squares = [(0, 0, 20, 20), (50, 0, 20, 20), (0, 50, 20, 20)]
        result = _snap_to_grid(squares)
        assert len(result) == 3

    @patch(NP)
    def test_single_square_no_gaps(self, mock_np: MagicMock) -> None:
        mock_np.median.return_value = 30
        mock_np.mean.side_effect = lambda c: sum(c) / len(c)

        squares = [(10, 10, 20, 20)]
        result = _snap_to_grid(squares)
        assert len(result) == 1


# ── _classify_one ────────────────────────────────────────────────────


class TestClassifyOne:
    def test_tiny_interior_returns_normal(self) -> None:
        gray = MagicMock()
        # bbox (0,0,5,5), border = max(3, min(5,5)//5) = max(3,1) = 3
        # ix1=3, ix2=5-3=2 → ix2<=ix1 → "normal"
        result = _classify_one(gray, (0, 0, 5, 5))
        assert result == ("normal", {})

    @patch(NP)
    def test_high_fill_is_player(self, mock_np: MagicMock) -> None:
        gray = MagicMock()
        interior = MagicMock()
        gray.__getitem__ = MagicMock(return_value=interior)
        mock_np.mean.return_value = 255 * 0.5  # fill = 0.5 > 0.40
        result = _classify_one(gray, (0, 0, 50, 50))
        assert result[0] == "player"

    @patch(NP)
    def test_low_fill_is_normal(self, mock_np: MagicMock) -> None:
        gray = MagicMock()
        interior = MagicMock()
        gray.__getitem__ = MagicMock(return_value=interior)
        mock_np.mean.return_value = 255 * 0.05  # fill = 0.05 < 0.12
        result = _classify_one(gray, (0, 0, 50, 50))
        assert result[0] == "normal"


# ── _classify_by_fill ───────────────────────────────────────────────


class TestClassifyByFill:
    def test_player(self) -> None:
        result = _classify_by_fill(0.5, MagicMock(), (0, 0, 50, 50), MagicMock())
        assert result == ("player", {})

    def test_normal(self) -> None:
        result = _classify_by_fill(0.05, MagicMock(), (0, 0, 50, 50), MagicMock())
        assert result == ("normal", {})

    @patch("python_pkg.puzzle_solver.parse_image._detect_antenna")
    def test_teleporter(self, mock_antenna: MagicMock) -> None:
        mock_antenna.return_value = ["up"]
        result = _classify_by_fill(0.2, MagicMock(), (0, 0, 50, 50), MagicMock())
        assert result is not None
        assert result[0] == "teleporter"
        assert result[1] == {"antenna_sides": ["up"]}

    @patch("python_pkg.puzzle_solver.parse_image._is_ring_pattern")
    @patch("python_pkg.puzzle_solver.parse_image._detect_antenna")
    def test_goal(self, mock_antenna: MagicMock, mock_ring: MagicMock) -> None:
        mock_antenna.return_value = None
        mock_ring.return_value = True
        result = _classify_by_fill(0.2, MagicMock(), (0, 0, 50, 50), MagicMock())
        assert result == ("goal", {})

    @patch("python_pkg.puzzle_solver.parse_image._classify_interior_feature")
    @patch("python_pkg.puzzle_solver.parse_image._is_ring_pattern")
    @patch("python_pkg.puzzle_solver.parse_image._detect_antenna")
    def test_delegates_to_interior_feature(
        self,
        mock_antenna: MagicMock,
        mock_ring: MagicMock,
        mock_interior: MagicMock,
    ) -> None:
        mock_antenna.return_value = None
        mock_ring.return_value = False
        mock_interior.return_value = ("portal", {"side": "left"})
        result = _classify_by_fill(0.2, MagicMock(), (0, 0, 50, 50), MagicMock())
        assert result == ("portal", {"side": "left"})


# ── _classify_interior_feature ──────────────────────────────────────


class TestClassifyInteriorFeature:
    @patch("python_pkg.puzzle_solver.parse_image._detect_portal_side")
    def test_portal(self, mock_portal: MagicMock) -> None:
        mock_portal.return_value = "left"
        result = _classify_interior_feature(0.2, MagicMock())
        assert result == ("portal", {"side": "left"})

    @patch("python_pkg.puzzle_solver.parse_image._has_interior_feature")
    @patch("python_pkg.puzzle_solver.parse_image._detect_portal_side")
    def test_key_or_lock(self, mock_portal: MagicMock, mock_feat: MagicMock) -> None:
        mock_portal.return_value = None
        mock_feat.return_value = True
        result = _classify_interior_feature(0.2, MagicMock())
        assert result is not None
        assert result[0] == "key_or_lock"
        assert result[1] == {"fill_ratio": 0.2}

    @patch("python_pkg.puzzle_solver.parse_image._has_interior_feature")
    @patch("python_pkg.puzzle_solver.parse_image._detect_portal_side")
    def test_none(self, mock_portal: MagicMock, mock_feat: MagicMock) -> None:
        mock_portal.return_value = None
        mock_feat.return_value = False
        result = _classify_interior_feature(0.2, MagicMock())
        assert result is None


# ── _classify_one (unknown) ─────────────────────────────────────────


class TestClassifyOneUnknown:
    @patch("python_pkg.puzzle_solver.parse_image._classify_by_fill")
    @patch(NP)
    def test_unknown_when_classify_by_fill_is_none(
        self, mock_np: MagicMock, mock_cbf: MagicMock
    ) -> None:
        gray = MagicMock()
        interior = MagicMock()
        gray.__getitem__ = MagicMock(return_value=interior)
        mock_np.mean.return_value = 255 * 0.2
        mock_cbf.return_value = None
        result = _classify_one(gray, (0, 0, 50, 50))
        assert result[0] == "unknown"
        assert "fill_ratio" in result[1]


# ── _detect_antenna ──────────────────────────────────────────────────


class TestDetectAntenna:
    @patch(NP)
    def test_all_sides_detected(self, mock_np: MagicMock) -> None:
        gray = MagicMock()
        gray.shape = (200, 200)
        strip = MagicMock()
        strip.size = 100
        gray.__getitem__ = MagicMock(return_value=strip)
        mock_np.mean.return_value = 255 * 0.2  # > 0.08

        result = _detect_antenna(gray, (50, 50, 40, 40))
        assert result is not None
        assert "up" in result
        assert "down" in result
        assert "left" in result
        assert "right" in result

    @patch(NP)
    def test_no_sides(self, mock_np: MagicMock) -> None:
        gray = MagicMock()
        gray.shape = (200, 200)
        strip = MagicMock()
        strip.size = 100
        gray.__getitem__ = MagicMock(return_value=strip)
        mock_np.mean.return_value = 255 * 0.01  # < 0.08

        result = _detect_antenna(gray, (50, 50, 40, 40))
        assert result is None

    @patch(NP)
    def test_edge_cases_no_margin(self, mock_np: MagicMock) -> None:
        gray = MagicMock()
        gray.shape = (50, 50)
        strip = MagicMock()
        strip.size = 100
        gray.__getitem__ = MagicMock(return_value=strip)
        mock_np.mean.return_value = 255 * 0.2

        # bbox at (0,0,50,50): all margin checks fail
        result = _detect_antenna(gray, (0, 0, 50, 50))
        assert result is None

    @patch(NP)
    def test_empty_strip(self, mock_np: MagicMock) -> None:
        gray = MagicMock()
        gray.shape = (200, 200)
        strip = MagicMock()
        strip.size = 0
        gray.__getitem__ = MagicMock(return_value=strip)

        result = _detect_antenna(gray, (50, 50, 40, 40))
        assert result is None


# ── _is_ring_pattern ────────────────────────────────────────────────


class TestIsRingPattern:
    def test_too_small(self) -> None:
        interior = MagicMock()
        interior.shape = (3, 3)
        assert _is_ring_pattern(interior) is False

    @patch(NP)
    @patch(CV2)
    def test_ring_found(self, mock_cv2: MagicMock, mock_np: MagicMock) -> None:
        interior = MagicMock()
        interior.shape = (20, 20)
        mock_cv2.threshold.return_value = (None, MagicMock())

        cnt = MagicMock()
        mock_cv2.findContours.return_value = ([cnt], None)
        mock_cv2.contourArea.return_value = 100.0
        mock_cv2.arcLength.return_value = 10.0
        mock_np.pi = 3.14159

        assert _is_ring_pattern(interior) is True

    @patch(NP)
    @patch(CV2)
    def test_ring_not_found_low_circ(
        self, mock_cv2: MagicMock, mock_np: MagicMock
    ) -> None:
        interior = MagicMock()
        interior.shape = (20, 20)
        mock_cv2.threshold.return_value = (None, MagicMock())

        cnt = MagicMock()
        mock_cv2.findContours.return_value = ([cnt], None)
        mock_cv2.contourArea.return_value = 1.0
        mock_cv2.arcLength.return_value = 100.0
        mock_np.pi = 3.14159

        assert _is_ring_pattern(interior) is False

    @patch(CV2)
    def test_ring_zero_perimeter(self, mock_cv2: MagicMock) -> None:
        interior = MagicMock()
        interior.shape = (20, 20)
        mock_cv2.threshold.return_value = (None, MagicMock())

        cnt = MagicMock()
        mock_cv2.findContours.return_value = ([cnt], None)
        mock_cv2.contourArea.return_value = 50.0
        mock_cv2.arcLength.return_value = 0

        assert _is_ring_pattern(interior) is False

    @patch(CV2)
    def test_no_contours(self, mock_cv2: MagicMock) -> None:
        interior = MagicMock()
        interior.shape = (20, 20)
        mock_cv2.threshold.return_value = (None, MagicMock())
        mock_cv2.findContours.return_value = ([], None)

        assert _is_ring_pattern(interior) is False


# ── _detect_portal_side ──────────────────────────────────────────────
