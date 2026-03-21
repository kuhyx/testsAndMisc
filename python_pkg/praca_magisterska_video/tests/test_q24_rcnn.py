"""Tests for _q24_rcnn module."""

from __future__ import annotations

import numpy as np


def test_rcnn_evolution() -> None:
    """_rcnn_evolution returns slides."""
    from python_pkg.praca_magisterska_video._q24_rcnn import _rcnn_evolution

    slides = _rcnn_evolution()
    assert isinstance(slides, list)
    assert len(slides) == 1


def test_rcnn_detailed() -> None:
    """_rcnn_detailed returns slides."""
    from python_pkg.praca_magisterska_video._q24_rcnn import _rcnn_detailed

    slides = _rcnn_detailed()
    assert isinstance(slides, list)
    assert len(slides) == 1


def test_draw_roi_pool_grid() -> None:
    """_draw_roi_pool_grid draws the 3x3 pooled output."""
    from python_pkg.praca_magisterska_video._q24_common import H, W
    from python_pkg.praca_magisterska_video._q24_rcnn import _draw_roi_pool_grid

    frame = np.zeros((H, W, 3), dtype=np.uint8)
    _draw_roi_pool_grid(frame)
    assert np.any(frame > 0)


def test_make_roi_frame() -> None:
    """_make_roi_frame generates frames at various times."""
    from python_pkg.praca_magisterska_video._q24_common import STEP_DUR, H, W
    from python_pkg.praca_magisterska_video._q24_rcnn import _make_roi_frame

    frame = _make_roi_frame(0.0)
    assert frame.shape == (H, W, 3)

    frame2 = _make_roi_frame(STEP_DUR * 0.9)
    assert frame2.shape == (H, W, 3)

    # Middle progress - arrow and grid visible but not FC
    frame3 = _make_roi_frame(STEP_DUR * 0.4)
    assert frame3.shape == (H, W, 3)


def test_roi_pooling_demo() -> None:
    """_roi_pooling_demo returns slides."""
    from python_pkg.praca_magisterska_video._q24_rcnn import _roi_pooling_demo

    slides = _roi_pooling_demo()
    assert isinstance(slides, list)
    assert len(slides) == 1
