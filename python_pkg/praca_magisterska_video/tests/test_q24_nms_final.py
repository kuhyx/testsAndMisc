"""Tests for _q24_nms_final module."""

from __future__ import annotations


def test_nms_iou_demo() -> None:
    """_nms_iou_demo returns slides with NMS and IoU animation."""
    from python_pkg.praca_magisterska_video._q24_nms_final import _nms_iou_demo

    slides = _nms_iou_demo()
    assert isinstance(slides, list)
    assert len(slides) == 1


def test_detector_from_classifier() -> None:
    """_detector_from_classifier returns slides for 3 approaches."""
    from python_pkg.praca_magisterska_video._q24_nms_final import (
        _detector_from_classifier,
    )

    slides = _detector_from_classifier()
    assert isinstance(slides, list)
    assert len(slides) == 3


def test_methods_comparison() -> None:
    """_methods_comparison returns a comparison table slide."""
    from python_pkg.praca_magisterska_video._q24_nms_final import _methods_comparison

    result = _methods_comparison()
    assert result is not None
