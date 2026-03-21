"""Tests for Q23 image-segmentation diagram modules (BATCH 3 / GROUP 1).

Covers:
  - _q23_common.py (constants, _save_figure, _render_text_lines)
  - _q23_architectures.py (generate_fcn, generate_unet)
  - _q23_diy_unet.py (generate_diy_unet, _draw_unet_layer_stack,
     _draw_unet_pseudocode)
  - _q23_mean_shift_ncuts.py (generate_mean_shift, generate_normalized_cuts,
     _draw_ncuts_pixel_grid, _draw_ncuts_edges)
  - _q23_mnemonics.py (generate_mnemonics)
  - _q23_nn_basics.py (generate_relu, generate_dot_product)
  - _q23_otsu_watershed.py (generate_otsu_bimodal, generate_watershed,
     _draw_otsu_variance_panel, _draw_watershed_result_panel)
  - _q23_receptive_transformer.py (generate_receptive_field, generate_transformer)
  - _q23_region_diy.py (generate_region_growing, generate_diy_thresholding,
     _draw_region_growing_grid, _draw_bfs_expansion,
     _draw_otsu_variance_and_pseudocode)
  - generate_q23_diagrams.py (__all__, imports, __main__ block)
"""

from __future__ import annotations

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pytest

pytestmark = pytest.mark.usefixtures("_no_savefig")


# ── _q23_common ───────────────────────────────────────────────────────


class TestQ23Constants:
    """Module-level constants and singletons."""

    def test_dpi(self) -> None:
        from _q23_common import DPI

        assert DPI == 300

    def test_output_dir_is_str(self) -> None:
        from _q23_common import OUTPUT_DIR

        assert isinstance(OUTPUT_DIR, str)

    def test_color_constants(self) -> None:
        from _q23_common import (
            ACCENT,
            ACCENT_LIGHT,
            BLACK,
            GRAY1,
            GRAY2,
            GRAY3,
            GRAY4,
            GRAY5,
            GRAY6,
            GREEN_ACCENT,
            RED_ACCENT,
            WHITE,
        )

        colors = [
            BLACK,
            WHITE,
            GRAY1,
            GRAY2,
            GRAY3,
            GRAY4,
            GRAY5,
            GRAY6,
            ACCENT,
            ACCENT_LIGHT,
            RED_ACCENT,
            GREEN_ACCENT,
        ]
        assert all(isinstance(c, str) and c.startswith("#") for c in colors)

    def test_font_size_constants(self) -> None:
        from _q23_common import FS, FS_SMALL, FS_TINY, FS_TITLE

        assert FS_TITLE > FS > FS_SMALL > FS_TINY

    def test_threshold_constants(self) -> None:
        from _q23_common import (
            _BRIGHT_THRESHOLD,
            _DARK_PIXEL_THRESHOLD,
            _GRID_LAST_IDX,
            _HIGHLIGHT_END,
            _HIGHLIGHT_START,
            _OTSU_THRESHOLD,
            _RIDGE_X,
            _VALLEY2_END,
        )

        assert _DARK_PIXEL_THRESHOLD == 100
        assert _GRID_LAST_IDX == 3
        assert _HIGHLIGHT_START == 3
        assert _HIGHLIGHT_END == 5
        assert _BRIGHT_THRESHOLD == 170
        assert _OTSU_THRESHOLD == 128
        assert _RIDGE_X == 5
        assert _VALLEY2_END == 9

    def test_rng_exists(self) -> None:
        from _q23_common import rng

        assert rng is not None


class TestQ23SaveFigure:
    """_save_figure from _q23_common."""

    def test_runs(self) -> None:
        from _q23_common import _save_figure

        _fig, _ax = plt.subplots()
        _save_figure("test_q23_save.png")


class TestQ23RenderTextLines:
    """_render_text_lines from _q23_common."""

    def test_basic_lines(self) -> None:
        from _q23_common import _render_text_lines

        fig, ax = plt.subplots()
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 10)
        lines = [
            ("Hello", 10, "black", "bold"),
            ("World", 8, "gray", "normal"),
        ]
        _render_text_lines(ax, lines, start_y=9.0)
        plt.close(fig)

    def test_empty_line_gaps(self) -> None:
        from _q23_common import _render_text_lines

        fig, ax = plt.subplots()
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 10)
        lines = [
            ("First", 10, "black", "bold"),
            ("", 0, "", ""),
            ("After gap", 10, "black", "normal"),
        ]
        _render_text_lines(ax, lines, start_y=9.0, y_step=0.5, y_empty_step=0.3)
        plt.close(fig)

    def test_custom_x_pos(self) -> None:
        from _q23_common import _render_text_lines

        fig, ax = plt.subplots()
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 10)
        lines = [("Test", 10, "red", "normal")]
        _render_text_lines(ax, lines, x_pos=0.3, start_y=8.0)
        plt.close(fig)


# ── _q23_architectures ───────────────────────────────────────────────


class TestGenerateFCN:
    """generate_fcn from _q23_architectures."""

    def test_runs(self) -> None:
        from _q23_architectures import generate_fcn

        generate_fcn()


class TestGenerateUNet:
    """generate_unet from _q23_architectures."""

    def test_runs(self) -> None:
        from _q23_architectures import generate_unet

        generate_unet()


# ── _q23_diy_unet ────────────────────────────────────────────────────


class TestDrawUnetLayerStack:
    """_draw_unet_layer_stack from _q23_diy_unet."""

    def test_without_skip(self) -> None:
        from _q23_diy_unet import _draw_unet_layer_stack

        fig, ax = plt.subplots()
        _draw_unet_layer_stack(
            ax,
            [(64, 3), (32, 64), (16, 128)],
            face_color="#B3D4FC",
            edge_color="#4A90D9",
            arrow_color="#4A90D9",
            arrow_label="Conv+Pool",
        )
        plt.close(fig)

    def test_with_skip(self) -> None:
        from _q23_diy_unet import _draw_unet_layer_stack

        fig, ax = plt.subplots()
        _draw_unet_layer_stack(
            ax,
            [(8, 256), (16, 128), (32, 64)],
            face_color="#C8E6C9",
            edge_color="#388E3C",
            arrow_color="#388E3C",
            arrow_label="UpConv+Concat",
            add_skip=True,
        )
        plt.close(fig)

    def test_single_layer_no_arrows(self) -> None:
        from _q23_diy_unet import _draw_unet_layer_stack

        fig, ax = plt.subplots()
        _draw_unet_layer_stack(
            ax,
            [(64, 3)],
            face_color="#B3D4FC",
            edge_color="#4A90D9",
            arrow_color="#4A90D9",
            arrow_label="X",
        )
        plt.close(fig)


class TestDrawUnetPseudocode:
    """_draw_unet_pseudocode from _q23_diy_unet."""

    def test_runs(self) -> None:
        from _q23_diy_unet import _draw_unet_pseudocode

        fig, ax = plt.subplots()
        _draw_unet_pseudocode(ax)
        plt.close(fig)


class TestGenerateDiyUnet:
    """generate_diy_unet from _q23_diy_unet."""

    @pytest.mark.filterwarnings("ignore::UserWarning")
    def test_runs(self) -> None:
        from _q23_diy_unet import generate_diy_unet

        generate_diy_unet()


# ── _q23_mean_shift_ncuts ────────────────────────────────────────────


class TestGenerateMeanShift:
    """generate_mean_shift from _q23_mean_shift_ncuts."""

    def test_runs(self) -> None:
        from _q23_mean_shift_ncuts import generate_mean_shift

        generate_mean_shift()


class TestDrawNcutsPixelGrid:
    """_draw_ncuts_pixel_grid from _q23_mean_shift_ncuts."""

    def test_runs(self) -> None:
        from _q23_mean_shift_ncuts import _draw_ncuts_pixel_grid

        fig, ax = plt.subplots()
        ax.set_xlim(-0.5, 4.5)
        ax.set_ylim(-0.5, 4.5)
        pixel_vals = np.array(
            [
                [30, 35, 180, 190],
                [40, 30, 185, 200],
                [170, 180, 40, 35],
                [190, 175, 30, 45],
            ]
        )
        _draw_ncuts_pixel_grid(ax, pixel_vals)
        plt.close(fig)

    def test_bright_pixels(self) -> None:
        """All pixels above dark threshold → black text."""
        from _q23_mean_shift_ncuts import _draw_ncuts_pixel_grid

        fig, ax = plt.subplots()
        ax.set_xlim(-0.5, 4.5)
        ax.set_ylim(-0.5, 4.5)
        bright = np.full((4, 4), 200)
        _draw_ncuts_pixel_grid(ax, bright)
        plt.close(fig)

    def test_dark_pixels(self) -> None:
        """All pixels below dark threshold → white text."""
        from _q23_mean_shift_ncuts import _draw_ncuts_pixel_grid

        fig, ax = plt.subplots()
        ax.set_xlim(-0.5, 4.5)
        ax.set_ylim(-0.5, 4.5)
        dark = np.full((4, 4), 50)
        _draw_ncuts_pixel_grid(ax, dark)
        plt.close(fig)


class TestDrawNcutsEdges:
    """_draw_ncuts_edges from _q23_mean_shift_ncuts."""

    def test_runs(self) -> None:
        from _q23_mean_shift_ncuts import _draw_ncuts_edges

        fig, ax = plt.subplots()
        ax.set_xlim(-0.5, 4.5)
        ax.set_ylim(-0.5, 4.5)
        pixel_vals = np.array(
            [
                [30, 35, 180, 190],
                [40, 30, 185, 200],
                [170, 180, 40, 35],
                [190, 175, 30, 45],
            ]
        )
        _draw_ncuts_edges(ax, pixel_vals)
        plt.close(fig)

    def test_uniform_values(self) -> None:
        """All same values → max similarity everywhere."""
        from _q23_mean_shift_ncuts import _draw_ncuts_edges

        fig, ax = plt.subplots()
        ax.set_xlim(-0.5, 4.5)
        ax.set_ylim(-0.5, 4.5)
        uniform = np.full((4, 4), 128)
        _draw_ncuts_edges(ax, uniform)
        plt.close(fig)


class TestGenerateNormalizedCuts:
    """generate_normalized_cuts from _q23_mean_shift_ncuts."""

    def test_runs(self) -> None:
        from _q23_mean_shift_ncuts import generate_normalized_cuts

        generate_normalized_cuts()


# ── _q23_mnemonics ───────────────────────────────────────────────────


class TestGenerateMnemonics:
    """generate_mnemonics from _q23_mnemonics."""

    def test_runs(self) -> None:
        from _q23_mnemonics import generate_mnemonics

        generate_mnemonics()


# ── _q23_nn_basics ───────────────────────────────────────────────────


class TestGenerateRelu:
    """generate_relu from _q23_nn_basics."""

    def test_runs(self) -> None:
        from _q23_nn_basics import generate_relu

        generate_relu()


class TestGenerateDotProduct:
    """generate_dot_product from _q23_nn_basics."""

    def test_runs(self) -> None:
        from _q23_nn_basics import generate_dot_product

        generate_dot_product()


# ── _q23_otsu_watershed ──────────────────────────────────────────────


class TestDrawOtsuVariancePanel:
    """_draw_otsu_variance_panel from _q23_otsu_watershed."""

    def test_runs(self) -> None:
        from _q23_otsu_watershed import _draw_otsu_variance_panel

        fig, ax = plt.subplots()
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 10)
        _draw_otsu_variance_panel(ax)
        plt.close(fig)


class TestGenerateOtsuBimodal:
    """generate_otsu_bimodal from _q23_otsu_watershed."""

    def test_runs(self) -> None:
        from _q23_otsu_watershed import generate_otsu_bimodal

        generate_otsu_bimodal()


class TestDrawWatershedResultPanel:
    """_draw_watershed_result_panel from _q23_otsu_watershed."""

    def test_runs(self) -> None:
        from _q23_otsu_watershed import _draw_watershed_result_panel

        fig, ax = plt.subplots()
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 10)
        _draw_watershed_result_panel(ax)
        plt.close(fig)


class TestGenerateWatershed:
    """generate_watershed from _q23_otsu_watershed."""

    def test_runs(self) -> None:
        from _q23_otsu_watershed import generate_watershed

        generate_watershed()


# ── _q23_receptive_transformer ───────────────────────────────────────


class TestGenerateReceptiveField:
    """generate_receptive_field from _q23_receptive_transformer."""

    def test_runs(self) -> None:
        from _q23_receptive_transformer import generate_receptive_field

        generate_receptive_field()


class TestGenerateTransformer:
    """generate_transformer from _q23_receptive_transformer."""

    def test_runs(self) -> None:
        from _q23_receptive_transformer import generate_transformer

        generate_transformer()


# ── _q23_region_diy ──────────────────────────────────────────────────


class TestDrawRegionGrowingGrid:
    """_draw_region_growing_grid from _q23_region_diy."""

    def test_runs(self) -> None:
        from _q23_region_diy import _draw_region_growing_grid

        fig, ax = plt.subplots()
        _draw_region_growing_grid(ax)
        plt.close(fig)

    def test_bright_pixels_in_region(self) -> None:
        """Hit elif branch: masked pixel >= _BRIGHT_THRESHOLD."""
        from unittest.mock import patch

        from _q23_region_diy import _draw_region_growing_grid

        fig, ax = plt.subplots()
        with patch("_q23_region_diy._BRIGHT_THRESHOLD", 0):
            _draw_region_growing_grid(ax)
        plt.close(fig)


class TestDrawBfsExpansion:
    """_draw_bfs_expansion from _q23_region_diy."""

    def test_runs(self) -> None:
        from _q23_region_diy import _draw_bfs_expansion

        fig, ax = plt.subplots()
        _draw_bfs_expansion(ax)
        plt.close(fig)


class TestGenerateRegionGrowing:
    """generate_region_growing from _q23_region_diy."""

    def test_runs(self) -> None:
        from _q23_region_diy import generate_region_growing

        generate_region_growing()
