"""MoviePy visualization for PYTANIE 24: Object Detection.

Creates animated video demonstrating:
- What detection is (bounding box + class + confidence)
- HOG + SVM pipeline (gradient → histogram → classify)
- Viola-Jones (Haar features, integral image, cascade)
- R-CNN evolution (R-CNN → Fast → Faster)
- YOLO one-stage detection
- Building a detector from a classifier
"""

from __future__ import annotations

import logging
import os

os.environ["FFMPEG_BINARY"] = "/usr/bin/ffmpeg"

from _q24_classical import (
    _detection_concept,
    _hog_svm_demo,
    _viola_jones_demo,
)
from _q24_common import FPS, OUTPUT, _logger, _make_header
from _q24_nms_final import (
    _detector_from_classifier,
    _methods_comparison,
    _nms_iou_demo,
)
from _q24_rcnn import (
    _rcnn_detailed,
    _rcnn_evolution,
    _roi_pooling_demo,
)
from _q24_rpn_yolo import _rpn_anchors_demo, _yolo_demo
from _q24_yolo_arch_detr import _detr_demo, _yolo_architecture
from moviepy import VideoClip, concatenate_videoclips


# ── Main ──────────────────────────────────────────────────────────
def main() -> None:
    """Generate the Q24 object detection visualization video."""
    sections: list[VideoClip] = []

    sections.append(
        _make_header(
            "Pytanie 24: Detekcja obiektów",
            "Problem, metody klasyczne, deep learning",
            duration=4.0,
        )
    )

    # What is detection
    sections.append(
        _make_header("Co to detekcja?", "Lokalizacja (bbox) + klasyfikacja (klasa)")
    )
    sections.extend(_detection_concept())

    # HOG + SVM
    sections.append(
        _make_header("HOG + SVM (2005)", "Klasyczny pipeline — gradient histogramy")
    )
    sections.extend(_hog_svm_demo())

    # Viola-Jones
    sections.append(
        _make_header("Viola-Jones (2001)", "Haar features + Integral Image + Cascade")
    )
    sections.extend(_viola_jones_demo())

    # R-CNN evolution (overview)
    sections.append(_make_header("Ewolucja R-CNN", "R-CNN → Fast R-CNN → Faster R-CNN"))
    sections.extend(_rcnn_evolution())

    # R-CNN detailed pipeline
    sections.append(
        _make_header("R-CNN: krok po kroku", "Selective Search → 2000xCNN → SVM → NMS")
    )
    sections.extend(_rcnn_detailed())

    # ROI Pooling
    sections.append(
        _make_header("ROI Pooling (Fast R-CNN)", "CNN raz + ROI Pool → 25x szybciej")
    )
    sections.extend(_roi_pooling_demo())

    # RPN + Anchors
    sections.append(
        _make_header("RPN + Anchor Boxes", "Faster R-CNN: propozycje W SIECI")
    )
    sections.extend(_rpn_anchors_demo())

    # YOLO
    sections.append(
        _make_header("YOLO (2016)", "You Only Look Once — jednoetapowy detektor")
    )
    sections.extend(_yolo_demo())

    # YOLO architecture detail
    sections.append(
        _make_header("YOLO: Architektura", "Backbone → Neck → Head → tensor SxS")
    )
    sections.extend(_yolo_architecture())

    # DETR
    sections.append(_make_header("DETR (2020)", "Transformer: bez NMS, bez anchorów!"))
    sections.extend(_detr_demo())

    # NMS + IoU
    sections.append(_make_header("NMS + IoU", "Post-processing — usuwanie duplikatów"))
    sections.extend(_nms_iou_demo())

    # Detector from classifier
    sections.append(
        _make_header(
            "Detektor z klasyfikatora", "3 podejścia: Sliding → Region → Fine-tune"
        )
    )
    sections.extend(_detector_from_classifier())

    # Comparison table
    sections.append(_methods_comparison())

    # Summary
    sections.append(
        _make_header(
            "Podsumowanie",
            "Klasyczne: HOG+SVM, Viola-Jones | DL: R-CNN, YOLO, DETR",
            duration=4.0,
        )
    )

    final = concatenate_videoclips(sections, method="compose")
    final.write_videofile(
        OUTPUT, fps=FPS, codec="libx264", audio=False, preset="medium", threads=4
    )
    _logger.info("Video saved to: %s", OUTPUT)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
