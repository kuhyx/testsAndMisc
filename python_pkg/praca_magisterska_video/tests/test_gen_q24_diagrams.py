"""Tests for Q24 object-detection diagram modules (BATCH 3 / GROUP 2).

Covers:
  - generate_images/_q24_common.py (draw_box, draw_arrow, save_fig,
     draw_table, constants)
  - _q24_fpn_tasks_cnn.py (draw_fpn, draw_anchor_boxes,
     draw_detection_tasks, draw_cnn_architecture)
  - _q24_haar_integral_svm.py (draw_haar_features, _draw_haar_face_panel,
     draw_integral_image, draw_svm_hyperplane)
  - _q24_hog_classical.py (draw_hog_svm_pipeline, draw_hog_gradient_steps,
     draw_viola_jones_cascade)
  - _q24_iou_nms_detector.py (draw_iou_diagram, draw_nms_steps,
     draw_detector_from_classifier)
  - _q24_modern_pipelines.py (draw_two_vs_one_stage, draw_roi_pooling,
     draw_detr_pipeline, draw_sliding_window)
  - _q24_rcnn_yolo.py (draw_rcnn_evolution, draw_yolo_grid,
     _draw_yolo_cell_prediction)
  - generate_q24_diagrams.py (__all__, imports)
"""

from __future__ import annotations

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
import pytest

pytestmark = pytest.mark.usefixtures("_no_savefig")


# ── generate_images/_q24_common ──────────────────────────────────────
# NOTE: This is the generate_images-level _q24_common, NOT the top-level
# praca_magisterska_video/_q24_common (which is for moviepy videos).


class TestGenQ24CommonConstants:
    """Module-level constants from generate_images/_q24_common."""

    def test_dpi(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images._q24_common import DPI

        # The generate_images _q24_common has DPI=300
        assert DPI == 300

    def test_output_dir(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images._q24_common import (
            OUTPUT_DIR,
        )

        assert isinstance(OUTPUT_DIR, str)

    def test_bg_ln(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images._q24_common import (
            BG,
            LN,
        )

        assert BG == "white"
        assert LN == "black"

    def test_font_sizes(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images._q24_common import (
            FS,
            FS_LABEL,
            FS_SMALL,
            FS_TITLE,
        )

        assert FS_TITLE > FS_LABEL >= FS > FS_SMALL

    def test_gray_palette(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images._q24_common import (
            GRAY1,
            GRAY2,
            GRAY3,
            GRAY4,
            GRAY5,
        )

        grays = [GRAY1, GRAY2, GRAY3, GRAY4, GRAY5]
        assert all(isinstance(g, str) and g.startswith("#") for g in grays)

    def test_threshold_constants(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images._q24_common import (
            _DATA_BRIGHT_THRESH,
            _DOTS_STAGE_IDX,
            _GRADIENT_BRIGHT_THRESH,
            _II_BRIGHT_THRESH,
            _PIXEL_BRIGHT_THRESH,
        )

        assert _PIXEL_BRIGHT_THRESH == 127
        assert _GRADIENT_BRIGHT_THRESH == 100
        assert _DATA_BRIGHT_THRESH == 5
        assert _II_BRIGHT_THRESH == 25
        assert _DOTS_STAGE_IDX == 2

    def test_rng(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images._q24_common import rng

        assert rng is not None


class TestGenQ24DrawBox:
    """draw_box from generate_images/_q24_common."""

    def test_rounded(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images._q24_common import (
            draw_box,
        )

        fig, ax = plt.subplots()
        draw_box(ax, 0, 0, 2, 1, "test")
        plt.close(fig)

    def test_not_rounded(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images._q24_common import (
            draw_box,
        )

        fig, ax = plt.subplots()
        draw_box(ax, 0, 0, 2, 1, "test", rounded=False)
        plt.close(fig)

    def test_custom_style(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images._q24_common import (
            draw_box,
        )

        fig, ax = plt.subplots()
        draw_box(
            ax,
            0,
            0,
            2,
            1,
            "styled",
            fill="#CCC",
            lw=2.0,
            fontsize=12,
            fontweight="bold",
            ha="left",
            va="top",
            edgecolor="red",
            linestyle="--",
        )
        plt.close(fig)


class TestGenQ24DrawArrow:
    """draw_arrow from generate_images/_q24_common."""

    def test_default(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images._q24_common import (
            draw_arrow,
        )

        fig, ax = plt.subplots()
        draw_arrow(ax, 0, 0, 1, 1)
        plt.close(fig)

    def test_custom(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images._q24_common import (
            draw_arrow,
        )

        fig, ax = plt.subplots()
        draw_arrow(ax, 0, 0, 1, 1, lw=2.5, style="<->", color="red")
        plt.close(fig)


class TestGenQ24SaveFig:
    """save_fig from generate_images/_q24_common."""

    def test_save(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images._q24_common import (
            save_fig,
        )

        fig, _ax = plt.subplots()
        save_fig(fig, "test_q24_gen.png")


class TestGenQ24DrawTable:
    """draw_table from generate_images/_q24_common."""

    def test_basic(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images._q24_common import (
            draw_table,
        )

        fig, ax = plt.subplots()
        ax.set_xlim(0, 10)
        ax.set_ylim(-5, 2)
        draw_table(ax, ["A", "B"], [["1", "2"]], 0, 0, [2.0, 2.0])
        plt.close(fig)

    def test_custom_fills(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images._q24_common import (
            draw_table,
        )

        fig, ax = plt.subplots()
        ax.set_xlim(0, 10)
        ax.set_ylim(-5, 2)
        draw_table(
            ax,
            ["X"],
            [["a"], ["b"], ["c"]],
            0,
            0,
            [3.0],
            row_h=0.5,
            row_fills=["#EEE", "#DDD"],
            header_fontsize=10,
        )
        plt.close(fig)

    def test_row_fills_shorter_than_rows(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images._q24_common import (
            draw_table,
        )

        fig, ax = plt.subplots()
        ax.set_xlim(0, 10)
        ax.set_ylim(-10, 2)
        draw_table(
            ax,
            ["H"],
            [["r1"], ["r2"], ["r3"], ["r4"]],
            0,
            0,
            [3.0],
            row_fills=["#AAA"],
        )
        plt.close(fig)

    def test_no_row_fills(self) -> None:
        from python_pkg.praca_magisterska_video.generate_images._q24_common import (
            draw_table,
        )

        fig, ax = plt.subplots()
        ax.set_xlim(0, 10)
        ax.set_ylim(-5, 2)
        draw_table(ax, ["H"], [["r1"], ["r2"]], 0, 0, [3.0])
        plt.close(fig)

    def test_even_odd_alternation(self) -> None:
        """Rows alternate fill based on even/odd index."""
        from python_pkg.praca_magisterska_video.generate_images._q24_common import (
            draw_table,
        )

        fig, ax = plt.subplots()
        ax.set_xlim(0, 10)
        ax.set_ylim(-10, 2)
        draw_table(
            ax,
            ["H"],
            [["r1"], ["r2"], ["r3"]],
            0,
            0,
            [3.0],
        )
        plt.close(fig)


# ── _q24_fpn_tasks_cnn ──────────────────────────────────────────────


class TestDrawFPN:
    """draw_fpn from _q24_fpn_tasks_cnn."""

    def test_runs(self) -> None:
        from _q24_fpn_tasks_cnn import draw_fpn

        draw_fpn()


class TestDrawAnchorBoxes:
    """draw_anchor_boxes from _q24_fpn_tasks_cnn."""

    def test_runs(self) -> None:
        from _q24_fpn_tasks_cnn import draw_anchor_boxes

        draw_anchor_boxes()


class TestDrawDetectionTasks:
    """draw_detection_tasks from _q24_fpn_tasks_cnn."""

    def test_runs(self) -> None:
        from _q24_fpn_tasks_cnn import draw_detection_tasks

        draw_detection_tasks()


class TestDrawCNNArchitecture:
    """draw_cnn_architecture from _q24_fpn_tasks_cnn."""

    def test_runs(self) -> None:
        from _q24_fpn_tasks_cnn import draw_cnn_architecture

        draw_cnn_architecture()


# ── _q24_haar_integral_svm ──────────────────────────────────────────


class TestDrawHaarFeatures:
    """draw_haar_features from _q24_haar_integral_svm."""

    def test_runs(self) -> None:
        from _q24_haar_integral_svm import draw_haar_features

        draw_haar_features()


class TestDrawHaarFacePanel:
    """_draw_haar_face_panel from _q24_haar_integral_svm."""

    def test_runs(self) -> None:
        from _q24_haar_integral_svm import _draw_haar_face_panel

        fig, ax = plt.subplots()
        _draw_haar_face_panel(ax)
        plt.close(fig)


class TestDrawIntegralImage:
    """draw_integral_image from _q24_haar_integral_svm."""

    def test_runs(self) -> None:
        from _q24_haar_integral_svm import draw_integral_image

        draw_integral_image()


class TestDrawSVMHyperplane:
    """draw_svm_hyperplane from _q24_haar_integral_svm."""

    def test_runs(self) -> None:
        from _q24_haar_integral_svm import draw_svm_hyperplane

        draw_svm_hyperplane()


# ── _q24_hog_classical ──────────────────────────────────────────────


class TestDrawHogSVMPipeline:
    """draw_hog_svm_pipeline from _q24_hog_classical."""

    def test_runs(self) -> None:
        from _q24_hog_classical import draw_hog_svm_pipeline

        draw_hog_svm_pipeline()


class TestDrawHogGradientSteps:
    """draw_hog_gradient_steps from _q24_hog_classical."""

    def test_runs(self) -> None:
        from _q24_hog_classical import draw_hog_gradient_steps

        draw_hog_gradient_steps()


class TestDrawViolaJonesCascade:
    """draw_viola_jones_cascade from _q24_hog_classical."""

    def test_runs(self) -> None:
        from _q24_hog_classical import draw_viola_jones_cascade

        draw_viola_jones_cascade()


# ── _q24_iou_nms_detector ───────────────────────────────────────────


class TestDrawIoUDiagram:
    """draw_iou_diagram from _q24_iou_nms_detector."""

    def test_runs(self) -> None:
        from _q24_iou_nms_detector import draw_iou_diagram

        draw_iou_diagram()


class TestDrawNMSSteps:
    """draw_nms_steps from _q24_iou_nms_detector."""

    def test_runs(self) -> None:
        from _q24_iou_nms_detector import draw_nms_steps

        draw_nms_steps()


class TestDrawDetectorFromClassifier:
    """draw_detector_from_classifier from _q24_iou_nms_detector."""

    def test_runs(self) -> None:
        from _q24_iou_nms_detector import draw_detector_from_classifier

        draw_detector_from_classifier()


# ── _q24_modern_pipelines ───────────────────────────────────────────


class TestDrawTwoVsOneStage:
    """draw_two_vs_one_stage from _q24_modern_pipelines."""

    def test_runs(self) -> None:
        from _q24_modern_pipelines import draw_two_vs_one_stage

        draw_two_vs_one_stage()


class TestDrawROIPooling:
    """draw_roi_pooling from _q24_modern_pipelines."""

    def test_runs(self) -> None:
        from _q24_modern_pipelines import draw_roi_pooling

        draw_roi_pooling()


class TestDrawDETRPipeline:
    """draw_detr_pipeline from _q24_modern_pipelines."""

    def test_runs(self) -> None:
        from _q24_modern_pipelines import draw_detr_pipeline

        draw_detr_pipeline()


class TestDrawSlidingWindow:
    """draw_sliding_window from _q24_modern_pipelines."""

    def test_runs(self) -> None:
        from _q24_modern_pipelines import draw_sliding_window

        draw_sliding_window()
