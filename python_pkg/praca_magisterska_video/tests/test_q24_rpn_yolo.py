"""Tests for _q24_rpn_yolo module."""

from __future__ import annotations


def test_rpn_anchors_demo() -> None:
    """_rpn_anchors_demo returns slides."""
    from python_pkg.praca_magisterska_video._q24_rpn_yolo import _rpn_anchors_demo

    slides = _rpn_anchors_demo()
    assert isinstance(slides, list)
    assert len(slides) == 2


def test_yolo_demo() -> None:
    """_yolo_demo returns slides."""
    from python_pkg.praca_magisterska_video._q24_rpn_yolo import _yolo_demo

    slides = _yolo_demo()
    assert isinstance(slides, list)
    assert len(slides) == 1
