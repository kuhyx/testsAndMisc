"""Tests for pattern diagram modules (GROUP 1).

Covers:
  - generate_pattern_diagrams.py (draw_box, draw_arrow, constants)
  - _pattern_template_catalog.py (generate_pattern_template, generate_catalog_map)
  - _pattern_pillars_observer.py (generate_three_pillars, generate_observer_card_filled,
                                   _get_observer_band_height)
  - _pattern_navigation.py (generate_pattern_language_navigation)
"""

from __future__ import annotations

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
import pytest

from python_pkg.praca_magisterska_video.generate_images import (
    _pattern_pillars_observer as _pat_pillars,
)
from python_pkg.praca_magisterska_video.generate_images import (
    _pattern_template_catalog as _pat_tmpl,
)
from python_pkg.praca_magisterska_video.generate_images import (
    generate_pattern_diagrams as _pat_diags,
)
from python_pkg.praca_magisterska_video.generate_images._pattern_navigation import (
    generate_pattern_language_navigation,
)

pytestmark = pytest.mark.usefixtures("_no_savefig")

_GEN = "python_pkg.praca_magisterska_video.generate_images.generate_pattern_diagrams"
_TMPL = "python_pkg.praca_magisterska_video.generate_images._pattern_template_catalog"
_PILL = "python_pkg.praca_magisterska_video.generate_images._pattern_pillars_observer"
_NAV = "python_pkg.praca_magisterska_video.generate_images._pattern_navigation"


# ── generate_pattern_diagrams helpers ──────────────────────────────────


class TestPatternConstants:
    """Constants and module-level values."""

    def test_dpi(self) -> None:
        assert _pat_diags.DPI == 300

    def test_bg(self) -> None:
        assert _pat_diags.BG == "white"

    def test_gray_constants(self) -> None:
        assert all(
            isinstance(g, str)
            for g in [
                _pat_diags.GRAY1,
                _pat_diags.GRAY2,
                _pat_diags.GRAY3,
                _pat_diags.GRAY4,
                _pat_diags.GRAY5,
            ]
        )

    def test_band_heights(self) -> None:
        assert len(_pat_diags._BAND_HEIGHTS) == 5
        assert all(isinstance(h, float) for h in _pat_diags._BAND_HEIGHTS)

    def test_output_dir_is_str(self) -> None:
        assert isinstance(_pat_diags.OUTPUT_DIR, str)


class TestDrawBox:
    """Test draw_box helper."""

    def test_rounded(self) -> None:
        fig, ax = plt.subplots()
        _pat_diags.draw_box(ax, 0, 0, 1, 1, "test", rounded=True)
        plt.close(fig)

    def test_not_rounded(self) -> None:
        fig, ax = plt.subplots()
        _pat_diags.draw_box(ax, 0, 0, 1, 1, "test", rounded=False)
        plt.close(fig)

    def test_custom_style(self) -> None:
        fig, ax = plt.subplots()
        _pat_diags.draw_box(
            ax,
            0,
            0,
            2,
            2,
            "styled",
            fill="#CCC",
            lw=2.0,
            fontsize=12,
            fontweight="bold",
            ha="left",
            va="top",
            rounded=True,
        )
        plt.close(fig)


class TestDrawArrow:
    """Test draw_arrow helper."""

    def test_default(self) -> None:
        fig, ax = plt.subplots()
        _pat_diags.draw_arrow(ax, 0, 0, 1, 1)
        plt.close(fig)

    def test_custom(self) -> None:
        fig, ax = plt.subplots()
        _pat_diags.draw_arrow(ax, 0, 0, 1, 1, lw=2.5, style="<->", color="red")
        plt.close(fig)


# ── _pattern_template_catalog ──────────────────────────────────────────


class TestPatternTemplate:
    """Test generate_pattern_template."""

    def test_runs(self) -> None:
        _pat_tmpl.generate_pattern_template()


class TestCatalogMap:
    """Test generate_catalog_map."""

    def test_runs(self) -> None:
        _pat_tmpl.generate_catalog_map()


# ── _pattern_pillars_observer ──────────────────────────────────────────


class TestThreePillars:
    """Test generate_three_pillars."""

    def test_runs(self) -> None:
        _pat_pillars.generate_three_pillars()


class TestObserverCard:
    """Test generate_observer_card_filled."""

    def test_runs(self) -> None:
        _pat_pillars.generate_observer_card_filled()


class TestGetObserverBandHeight:
    """Test _get_observer_band_height."""

    def test_all_indices(self) -> None:
        for i in range(5):
            h = _pat_pillars._get_observer_band_height(i)
            assert isinstance(h, float)
            assert h > 0


# ── _pattern_navigation ───────────────────────────────────────────────


class TestPatternLanguageNavigation:
    """Test generate_pattern_language_navigation."""

    def test_runs(self) -> None:
        generate_pattern_language_navigation()
