"""Tests for Q24 object-detection diagram modules - part 2 (rcnn/yolo, top-level).

Covers:
  - _q24_rcnn_yolo.py (draw_rcnn_evolution, draw_yolo_grid,
     _draw_yolo_cell_prediction)
  - generate_q24_diagrams.py (__all__, imports)
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import pytest

pytestmark = pytest.mark.usefixtures("_no_savefig")


# ── _q24_rcnn_yolo ──────────────────────────────────────────────────


class TestDrawRCNNEvolution:
    """draw_rcnn_evolution from _q24_rcnn_yolo."""

    def test_runs(self) -> None:
        from _q24_rcnn_yolo import draw_rcnn_evolution

        draw_rcnn_evolution()


class TestDrawYoloGrid:
    """draw_yolo_grid from _q24_rcnn_yolo."""

    def test_runs(self) -> None:
        from _q24_rcnn_yolo import draw_yolo_grid

        draw_yolo_grid()


class TestDrawYoloCellPrediction:
    """_draw_yolo_cell_prediction from _q24_rcnn_yolo."""

    def test_runs(self) -> None:
        from _q24_rcnn_yolo import _draw_yolo_cell_prediction

        fig, ax = plt.subplots()
        _draw_yolo_cell_prediction(ax)
        plt.close(fig)


# ── generate_q24_diagrams ────────────────────────────────────────────


class TestGenerateQ24DiagramsModule:
    """generate_q24_diagrams top-level module."""

    def test_all_exports(self) -> None:
        import generate_q24_diagrams

        expected = {
            "draw_anchor_boxes",
            "draw_cnn_architecture",
            "draw_detection_tasks",
            "draw_detector_from_classifier",
            "draw_detr_pipeline",
            "draw_fpn",
            "draw_haar_features",
            "draw_hog_gradient_steps",
            "draw_hog_svm_pipeline",
            "draw_integral_image",
            "draw_iou_diagram",
            "draw_nms_steps",
            "draw_rcnn_evolution",
            "draw_roi_pooling",
            "draw_sliding_window",
            "draw_svm_hyperplane",
            "draw_two_vs_one_stage",
            "draw_viola_jones_cascade",
            "draw_yolo_grid",
        }
        assert set(generate_q24_diagrams.__all__) == expected

    def test_imports_callable(self) -> None:
        from generate_q24_diagrams import (
            draw_anchor_boxes,
            draw_cnn_architecture,
            draw_detection_tasks,
            draw_detector_from_classifier,
            draw_detr_pipeline,
            draw_fpn,
            draw_haar_features,
            draw_hog_gradient_steps,
            draw_hog_svm_pipeline,
            draw_integral_image,
            draw_iou_diagram,
            draw_nms_steps,
            draw_rcnn_evolution,
            draw_roi_pooling,
            draw_sliding_window,
            draw_svm_hyperplane,
            draw_two_vs_one_stage,
            draw_viola_jones_cascade,
            draw_yolo_grid,
        )

        fns = [
            draw_anchor_boxes,
            draw_cnn_architecture,
            draw_detection_tasks,
            draw_detector_from_classifier,
            draw_detr_pipeline,
            draw_fpn,
            draw_haar_features,
            draw_hog_gradient_steps,
            draw_hog_svm_pipeline,
            draw_integral_image,
            draw_iou_diagram,
            draw_nms_steps,
            draw_rcnn_evolution,
            draw_roi_pooling,
            draw_sliding_window,
            draw_svm_hyperplane,
            draw_two_vs_one_stage,
            draw_viola_jones_cascade,
            draw_yolo_grid,
        ]
        assert all(callable(f) for f in fns)
