#!/usr/bin/env python3
"""Generate ALL diagrams for PYTANIE 24: Detekcja obiektów.

Monochrome, A4-printable PNGs (300 DPI).
Re-exports all diagram generators from submodules.
"""

from __future__ import annotations

import logging
from pathlib import Path
import sys

# Ensure sibling modules are importable when run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _q24_common import OUTPUT_DIR
from _q24_fpn_tasks_cnn import (
    draw_anchor_boxes,
    draw_cnn_architecture,
    draw_detection_tasks,
    draw_fpn,
)
from _q24_haar_integral_svm import (
    draw_haar_features,
    draw_integral_image,
    draw_svm_hyperplane,
)
from _q24_hog_classical import (
    draw_hog_gradient_steps,
    draw_hog_svm_pipeline,
    draw_viola_jones_cascade,
)
from _q24_iou_nms_detector import (
    draw_detector_from_classifier,
    draw_iou_diagram,
    draw_nms_steps,
)
from _q24_modern_pipelines import (
    draw_detr_pipeline,
    draw_roi_pooling,
    draw_sliding_window,
    draw_two_vs_one_stage,
)
from _q24_rcnn_yolo import draw_rcnn_evolution, draw_yolo_grid

__all__ = [
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
]

_logger = logging.getLogger(__name__)

# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    _logger.info("Generating PYTANIE 24 diagrams...")
    draw_hog_svm_pipeline()
    draw_hog_gradient_steps()
    draw_viola_jones_cascade()
    draw_haar_features()
    draw_integral_image()
    draw_rcnn_evolution()
    draw_yolo_grid()
    draw_iou_diagram()
    draw_nms_steps()
    draw_detector_from_classifier()
    draw_svm_hyperplane()
    draw_two_vs_one_stage()
    draw_roi_pooling()
    draw_detr_pipeline()
    draw_sliding_window()
    draw_fpn()
    draw_anchor_boxes()
    draw_detection_tasks()
    draw_cnn_architecture()
    _logger.info("All PYTANIE 24 diagrams saved to: %s", OUTPUT_DIR)
