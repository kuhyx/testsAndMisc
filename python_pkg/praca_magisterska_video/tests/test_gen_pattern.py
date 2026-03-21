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

pytestmark = pytest.mark.usefixtures("_no_savefig")

_GEN = "python_pkg.praca_magisterska_video.generate_images.generate_pattern_diagrams"
_TMPL = "python_pkg.praca_magisterska_video.generate_images._pattern_template_catalog"
_PILL = "python_pkg.praca_magisterska_video.generate_images._pattern_pillars_observer"
_NAV = "python_pkg.praca_magisterska_video.generate_images._pattern_navigation"


# ── generate_pattern_diagrams helpers ──────────────────────────────────


class TestPatternConstants:
    """Constants and module-level values."""

    def test_dpi(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images.generate_pattern_diagrams import (
            DPI,
        )

        assert DPI == 300

    def test_bg(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images.generate_pattern_diagrams import (
            BG,
        )

        assert BG == "white"

    def test_gray_constants(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images.generate_pattern_diagrams import (
            GRAY1,
            GRAY2,
            GRAY3,
            GRAY4,
            GRAY5,
        )

        assert all(isinstance(g, str) for g in [GRAY1, GRAY2, GRAY3, GRAY4, GRAY5])

    def test_band_heights(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images.generate_pattern_diagrams import (
            _BAND_HEIGHTS,
        )

        assert len(_BAND_HEIGHTS) == 5
        assert all(isinstance(h, float) for h in _BAND_HEIGHTS)

    def test_output_dir_is_str(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images.generate_pattern_diagrams import (
            OUTPUT_DIR,
        )

        assert isinstance(OUTPUT_DIR, str)


class TestDrawBox:
    """Test draw_box helper."""

    def test_rounded(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images.generate_pattern_diagrams import (
            draw_box,
        )

        fig, ax = plt.subplots()
        draw_box(ax, 0, 0, 1, 1, "test", rounded=True)
        plt.close(fig)

    def test_not_rounded(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images.generate_pattern_diagrams import (
            draw_box,
        )

        fig, ax = plt.subplots()
        draw_box(ax, 0, 0, 1, 1, "test", rounded=False)
        plt.close(fig)

    def test_custom_style(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images.generate_pattern_diagrams import (
            draw_box,
        )

        fig, ax = plt.subplots()
        draw_box(
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
        from python_pkg.praca_magisterska_video.generate_images.generate_pattern_diagrams import (
            draw_arrow,
        )

        fig, ax = plt.subplots()
        draw_arrow(ax, 0, 0, 1, 1)
        plt.close(fig)

    def test_custom(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images.generate_pattern_diagrams import (
            draw_arrow,
        )

        fig, ax = plt.subplots()
        draw_arrow(ax, 0, 0, 1, 1, lw=2.5, style="<->", color="red")
        plt.close(fig)


# ── _pattern_template_catalog ──────────────────────────────────────────


class TestPatternTemplate:
    """Test generate_pattern_template."""

    def test_runs(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images._pattern_template_catalog import (
            generate_pattern_template,
        )

        generate_pattern_template()


class TestCatalogMap:
    """Test generate_catalog_map."""

    def test_runs(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images._pattern_template_catalog import (
            generate_catalog_map,
        )

        generate_catalog_map()


# ── _pattern_pillars_observer ──────────────────────────────────────────


class TestThreePillars:
    """Test generate_three_pillars."""

    def test_runs(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images._pattern_pillars_observer import (
            generate_three_pillars,
        )

        generate_three_pillars()


class TestObserverCard:
    """Test generate_observer_card_filled."""

    def test_runs(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images._pattern_pillars_observer import (
            generate_observer_card_filled,
        )

        generate_observer_card_filled()


class TestGetObserverBandHeight:
    """Test _get_observer_band_height."""

    def test_all_indices(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images._pattern_pillars_observer import (
            _get_observer_band_height,
        )

        for i in range(5):
            h = _get_observer_band_height(i)
            assert isinstance(h, float)
            assert h > 0


# ── _pattern_navigation ───────────────────────────────────────────────


class TestPatternLanguageNavigation:
    """Test generate_pattern_language_navigation."""

    def test_runs(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images._pattern_navigation import (
            generate_pattern_language_navigation,
        )

        generate_pattern_language_navigation()
