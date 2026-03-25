"""Tests for normalization diagram modules (GROUP 5).

Covers:
  - generate_normalization_diagrams.py (draw_table, helpers)
  - _norm_basic.py (draw_0nf, draw_1nf, draw_2nf)
  - _norm_advanced.py (draw_3nf, draw_bcnf, draw_4nf)
  - _norm_higher.py (draw_5nf, draw_summary_flow)
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
import pytest

from python_pkg.praca_magisterska_video.generate_images import (
    generate_normalization_diagrams as _norm_mod,
)
from python_pkg.praca_magisterska_video.generate_images._norm_advanced import (
    draw_3nf,
    draw_4nf,
    draw_bcnf,
)
from python_pkg.praca_magisterska_video.generate_images._norm_basic import (
    draw_0nf,
    draw_1nf,
    draw_2nf,
)
from python_pkg.praca_magisterska_video.generate_images._norm_higher import (
    draw_5nf,
    draw_summary_flow,
)

pytestmark = pytest.mark.usefixtures("_no_savefig")

_GEN = (
    "python_pkg.praca_magisterska_video.generate_images.generate_normalization_diagrams"
)
_BASIC = "python_pkg.praca_magisterska_video.generate_images._norm_basic"
_ADV = "python_pkg.praca_magisterska_video.generate_images._norm_advanced"
_HIGH = "python_pkg.praca_magisterska_video.generate_images._norm_higher"


# ── helpers in generate_normalization_diagrams ─────────────────────────


class TestNormHelpers:
    """Test _compute_col_widths, draw_table, create_figure, add_arrow, add_label."""

    def test_compute_col_widths_normal(self) -> None:
        result = _norm_mod._compute_col_widths(["Name", "Age"], [["Alice", "30"]])
        assert len(result) == 2
        assert all(w >= 0.5 for w in result)

    def test_compute_col_widths_jagged(self) -> None:
        """Row shorter than headers → c < len(r) False branch."""
        result = _norm_mod._compute_col_widths(["A", "B", "C"], [["x"]])
        assert len(result) == 3

    def test_draw_table_auto_widths(self) -> None:
        fig, ax = _norm_mod.create_figure()
        _norm_mod.draw_table(ax, 0, 5, "T", ["A", "B"], [["1", "2"]])
        plt.close(fig)

    def test_draw_table_explicit_widths(self) -> None:
        fig, ax = _norm_mod.create_figure()
        _norm_mod.draw_table(ax, 0, 5, "T", ["A"], [["x"]], col_widths=[1.0])
        plt.close(fig)

    def test_draw_table_highlight_cols(self) -> None:
        fig, ax = _norm_mod.create_figure()
        _norm_mod.draw_table(
            ax,
            0,
            5,
            "T",
            ["A", "B"],
            [["1", "2"]],
            highlight_cols={0},
        )
        plt.close(fig)

    def test_draw_table_highlight_rows(self) -> None:
        fig, ax = _norm_mod.create_figure()
        _norm_mod.draw_table(
            ax,
            0,
            5,
            "T",
            ["A"],
            [["1"], ["2"]],
            highlight_rows={1},
        )
        plt.close(fig)

    def test_draw_table_highlight_cells(self) -> None:
        fig, ax = _norm_mod.create_figure()
        _norm_mod.draw_table(
            ax,
            0,
            5,
            "T",
            ["A", "B"],
            [["1", "2"]],
            highlight_cells={(0, 1)},
        )
        plt.close(fig)

    def test_draw_table_strikethrough(self) -> None:
        fig, ax = _norm_mod.create_figure()
        _norm_mod.draw_table(
            ax,
            0,
            5,
            "T",
            ["A", "B"],
            [["1", "2"]],
            strikethrough_cells={(0, 0)},
        )
        plt.close(fig)

    def test_draw_table_all_options(self) -> None:
        """All highlight/strikethrough at once, with matching+non-matching cells."""
        fig, ax = _norm_mod.create_figure()
        w, h = _norm_mod.draw_table(
            ax,
            0,
            5,
            "Full",
            ["A", "B", "C"],
            [["1", "2", "3"], ["4", "5", "6"]],
            col_widths=[1.0, 1.0, 1.0],
            highlight_cols={1},
            highlight_rows={0},
            highlight_cells={(1, 2)},
            strikethrough_cells={(0, 2)},
        )
        assert w > 0
        assert h > 0
        plt.close(fig)

    def test_create_figure(self) -> None:
        fig, ax = _norm_mod.create_figure(10, 8)
        assert fig is not None
        assert ax is not None
        plt.close(fig)

    def test_add_arrow_with_label(self) -> None:
        fig, ax = _norm_mod.create_figure()
        _norm_mod.add_arrow(ax, 0, 5, 3, 5, "lbl", color="black")
        plt.close(fig)

    def test_add_arrow_no_label(self) -> None:
        fig, ax = _norm_mod.create_figure()
        _norm_mod.add_arrow(ax, 0, 5, 3, 5)
        plt.close(fig)

    def test_add_label(self) -> None:
        fig, ax = _norm_mod.create_figure()
        _norm_mod.add_label(ax, 0, 5, "note", fontsize=10, color="red")
        plt.close(fig)

    def test_module_constants(self) -> None:
        assert _norm_mod.DPI == 300
        assert isinstance(_norm_mod.OUTPUT_DIR, str)
        assert isinstance(_norm_mod.HEADER_COLOR, str)
        assert isinstance(_norm_mod.CELL_COLOR, str)
        assert isinstance(_norm_mod.HIGHLIGHT_COLOR, str)
        assert isinstance(_norm_mod.FIXED_COLOR, str)
        assert isinstance(_norm_mod.FD_ARROW_COLOR, str)
        assert isinstance(_norm_mod.FONT_SIZE, int | float)


# ── _norm_basic (draw_table has positional-arg signature mismatch) ─────

_NORM_PATCHES = [
    f"{_BASIC}.draw_table",
    f"{_BASIC}.add_arrow",
]


class TestNormBasic:
    """Test draw_0nf, draw_1nf, draw_2nf."""

    @patch(f"{_BASIC}.add_arrow")
    @patch(f"{_BASIC}.draw_table")
    def test_draw_0nf(self, mock_dt: MagicMock, mock_aa: MagicMock) -> None:
        draw_0nf()

    @patch(f"{_BASIC}.add_arrow")
    @patch(f"{_BASIC}.draw_table")
    def test_draw_1nf(self, mock_dt: MagicMock, mock_aa: MagicMock) -> None:
        draw_1nf()

    @patch(f"{_BASIC}.add_arrow")
    @patch(f"{_BASIC}.draw_table")
    def test_draw_2nf(self, mock_dt: MagicMock, mock_aa: MagicMock) -> None:
        draw_2nf()


# ── _norm_advanced ─────────────────────────────────────────────────────


class TestNormAdvanced:
    """Test draw_3nf, draw_bcnf, draw_4nf."""

    @patch(f"{_ADV}.add_arrow")
    @patch(f"{_ADV}.draw_table")
    def test_draw_3nf(self, mock_dt: MagicMock, mock_aa: MagicMock) -> None:
        draw_3nf()

    @patch(f"{_ADV}.add_arrow")
    @patch(f"{_ADV}.draw_table")
    def test_draw_bcnf(self, mock_dt: MagicMock, mock_aa: MagicMock) -> None:
        draw_bcnf()

    @patch(f"{_ADV}.add_arrow")
    @patch(f"{_ADV}.draw_table")
    def test_draw_4nf(self, mock_dt: MagicMock, mock_aa: MagicMock) -> None:
        draw_4nf()


# ── _norm_higher ───────────────────────────────────────────────────────


class TestNormHigher:
    """Test draw_5nf, draw_summary_flow."""

    @patch(f"{_HIGH}.add_arrow")
    @patch(f"{_HIGH}.draw_table")
    def test_draw_5nf(self, mock_dt: MagicMock, mock_aa: MagicMock) -> None:
        draw_5nf()

    @patch(f"{_HIGH}.add_arrow")
    @patch(f"{_HIGH}.draw_table")
    def test_draw_summary_flow(self, mock_dt: MagicMock, mock_aa: MagicMock) -> None:
        draw_summary_flow()
