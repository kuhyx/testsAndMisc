"""Tests for _q23_unet_fcn module."""

from __future__ import annotations

import numpy as np


def test_draw_unet_skips_below_threshold() -> None:
    """_draw_unet_skips does nothing when n_blocks <= skip_threshold."""
    from python_pkg.praca_magisterska_video._q23_helpers import H, W
    from python_pkg.praca_magisterska_video._q23_unet_fcn import _draw_unet_skips

    frame = np.zeros((H, W, 3), dtype=np.uint8)
    enc_positions = [(150, 120, 80, 120), (150, 250, 60, 100)]
    _draw_unet_skips(frame, enc_positions, n_blocks=3, dec_x=850, skip_threshold=5)
    assert not np.any(frame > 0)


def test_draw_unet_skips_above_threshold() -> None:
    """_draw_unet_skips draws dashed lines when n_blocks > skip_threshold."""
    from python_pkg.praca_magisterska_video._q23_helpers import H, W
    from python_pkg.praca_magisterska_video._q23_unet_fcn import _draw_unet_skips

    frame = np.zeros((H, W, 3), dtype=np.uint8)
    enc_positions = [
        (150, 120, 80, 120),
        (150, 250, 60, 100),
        (150, 380, 45, 80),
        (150, 510, 30, 60),
    ]
    _draw_unet_skips(frame, enc_positions, n_blocks=8, dec_x=850, skip_threshold=5)
    assert np.any(frame > 0)


def test_make_unet_frame() -> None:
    """_make_unet_frame generates valid frames at various times."""
    from python_pkg.praca_magisterska_video._q23_helpers import STEP_DUR, H, W
    from python_pkg.praca_magisterska_video._q23_unet_fcn import _make_unet_frame

    # At t=0, minimal blocks visible
    frame = _make_unet_frame(0.0)
    assert frame.shape == (H, W, 3)

    # At high time, all blocks visible including bottleneck
    frame2 = _make_unet_frame(STEP_DUR * 0.9)
    assert frame2.shape == (H, W, 3)

    # Mid-progress (bottleneck visible, some decoder)
    frame3 = _make_unet_frame(STEP_DUR * 0.4)
    assert frame3.shape == (H, W, 3)


def test_unet_demo() -> None:
    """_unet_demo returns slides."""
    from python_pkg.praca_magisterska_video._q23_unet_fcn import _unet_demo

    slides = _unet_demo()
    assert isinstance(slides, list)
    assert len(slides) == 1


def test_draw_pipeline_blocks() -> None:
    """_draw_pipeline_blocks draws coloured blocks."""
    from python_pkg.praca_magisterska_video._q23_helpers import H, W
    from python_pkg.praca_magisterska_video._q23_unet_fcn import _draw_pipeline_blocks

    frame = np.zeros((H, W, 3), dtype=np.uint8)
    blocks = [
        ((80, 140), (70, 50), (70, 130, 200)),
        ((170, 140), (50, 40), (50, 100, 160)),
    ]
    _draw_pipeline_blocks(frame, blocks, n_visible=2, arrow_limit=1)
    assert np.any(frame > 0)


def test_draw_pipeline_blocks_no_visible() -> None:
    """_draw_pipeline_blocks with n_visible=0 draws nothing."""
    from python_pkg.praca_magisterska_video._q23_helpers import H, W
    from python_pkg.praca_magisterska_video._q23_unet_fcn import _draw_pipeline_blocks

    frame = np.zeros((H, W, 3), dtype=np.uint8)
    blocks = [((80, 140), (70, 50), (70, 130, 200))]
    _draw_pipeline_blocks(frame, blocks, n_visible=0, arrow_limit=1)
    assert not np.any(frame > 0)


def test_draw_red_cross() -> None:
    """_draw_red_cross draws an X on the frame."""
    from python_pkg.praca_magisterska_video._q23_helpers import H, W
    from python_pkg.praca_magisterska_video._q23_unet_fcn import _draw_red_cross

    frame = np.zeros((H, W, 3), dtype=np.uint8)
    _draw_red_cross(frame, 385, 135, 140, 50)
    assert np.any(frame > 0)


def test_draw_red_cross_out_of_bounds() -> None:
    """_draw_red_cross with coords near edges triggers bounds checks."""
    import python_pkg.praca_magisterska_video._q23_unet_fcn as mod

    orig_h, orig_w = mod.H, mod.W
    try:
        mod.H = 20
        mod.W = 20
        frame = np.zeros((20, 20, 3), dtype=np.uint8)
        mod._draw_red_cross(frame, x_start=0, width=30, top_y=0, height=25)
        assert frame.shape == (20, 20, 3)
    finally:
        mod.H = orig_h
        mod.W = orig_w


def test_make_fcn_frame() -> None:
    """_make_fcn_frame generates valid frames at various times."""
    from python_pkg.praca_magisterska_video._q23_helpers import STEP_DUR, H, W
    from python_pkg.praca_magisterska_video._q23_unet_fcn import _make_fcn_frame

    # Early: only classic pipeline visible
    frame = _make_fcn_frame(0.0)
    assert frame.shape == (H, W, 3)

    # Late: all blocks, cross, FCN blocks visible
    frame2 = _make_fcn_frame(STEP_DUR * 0.9)
    assert frame2.shape == (H, W, 3)

    # Mid: FCN blocks starting to appear
    frame3 = _make_fcn_frame(STEP_DUR * 0.5)
    assert frame3.shape == (H, W, 3)


def test_fcn_demo() -> None:
    """_fcn_demo returns slides."""
    from python_pkg.praca_magisterska_video._q23_unet_fcn import _fcn_demo

    slides = _fcn_demo()
    assert isinstance(slides, list)
    assert len(slides) >= 1
