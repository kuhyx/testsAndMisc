"""Tests for architecture diagram modules (GROUP 2).

Covers:
  - generate_arch_diagrams.py (helpers, TOGAF ADM, 4+1 View)
  - _arch_c4.py (C4 model diagrams)
  - _arch_layers.py (Zachman, ArchiMate)
"""

from __future__ import annotations

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
import pytest

pytestmark = pytest.mark.usefixtures("_no_savefig")


# ── helpers in generate_arch_diagrams ──────────────────────────────────


class TestArchHelpers:
    """Test draw_box (rounded/default), draw_arrow, draw_line, _draw_class."""

    def test_draw_box_rounded(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images.generate_arch_diagrams import (
            draw_box,
        )

        fig, ax = plt.subplots()
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 100)
        draw_box(ax, 5, 5, 20, 10, "text", rounded=True)
        plt.close(fig)

    def test_draw_box_default(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images.generate_arch_diagrams import (
            draw_box,
        )

        fig, ax = plt.subplots()
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 100)
        draw_box(ax, 5, 5, 20, 10, "text")
        plt.close(fig)

    def test_draw_arrow(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images.generate_arch_diagrams import (
            draw_arrow,
        )

        fig, ax = plt.subplots()
        draw_arrow(ax, 0, 0, 1, 1)
        plt.close(fig)

    def test_draw_line(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images.generate_arch_diagrams import (
            draw_line,
        )

        fig, ax = plt.subplots()
        draw_line(ax, 0, 0, 1, 1, lw=1.0, ls="--")
        plt.close(fig)

    def test_draw_class(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images.generate_arch_diagrams import (
            _draw_class,
        )

        fig, ax = plt.subplots()
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 100)
        _draw_class(ax, 5, 5, "Cls", ["-x: int"], ["+get()"])
        plt.close(fig)

    def test_draw_class_empty(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images.generate_arch_diagrams import (
            _draw_class,
        )

        fig, ax = plt.subplots()
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 100)
        _draw_class(ax, 5, 5, "Empty", [], [])
        plt.close(fig)


# ── Diagram generation functions ───────────────────────────────────────


class TestArchDiagrams:
    """Test all top-level generate functions."""

    def test_generate_togaf_adm(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images.generate_arch_diagrams import (
            generate_togaf_adm,
        )

        generate_togaf_adm()

    def test_generate_4plus1(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images.generate_arch_diagrams import (
            generate_4plus1,
        )

        generate_4plus1()

    def test_generate_c4(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images._arch_c4 import (
            generate_c4,
        )

        generate_c4()

    def test_generate_zachman(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images._arch_layers import (
            generate_zachman,
        )

        generate_zachman()

    def test_generate_archimate(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images._arch_layers import (
            generate_archimate,
        )

        generate_archimate()


class TestArchModuleImports:
    """Verify module-level constants are accessible."""

    def test_arch_module_constants(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images.generate_arch_diagrams import (
            BG,
            DPI,
            FS,
            FS_TITLE,
            GRAY1,
            GRAY2,
            GRAY3,
            GRAY4,
            LN,
            OUTPUT_DIR,
        )

        assert DPI == 300
        assert BG == "white"
        assert LN == "black"
        assert FS == 9
        assert FS_TITLE == 14
        assert isinstance(GRAY1, str)
        assert isinstance(GRAY2, str)
        assert isinstance(GRAY3, str)
        assert isinstance(GRAY4, str)
        assert isinstance(OUTPUT_DIR, str)
