"""Tests for _q24_yolo_arch_detr module."""

from __future__ import annotations


def test_yolo_architecture() -> None:
    """_yolo_architecture returns slides."""
    from python_pkg.praca_magisterska_video._q24_yolo_arch_detr import (
        _yolo_architecture,
    )

    slides = _yolo_architecture()
    assert isinstance(slides, list)
    assert len(slides) == 1


def test_detr_demo() -> None:
    """_detr_demo returns slides (pipeline + details + summary)."""
    from python_pkg.praca_magisterska_video._q24_yolo_arch_detr import _detr_demo

    slides = _detr_demo()
    assert isinstance(slides, list)
    assert len(slides) == 3
