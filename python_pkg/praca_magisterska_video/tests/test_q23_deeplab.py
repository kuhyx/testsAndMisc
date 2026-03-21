"""Tests for _q23_deeplab module."""

from __future__ import annotations


def test_make_dilated_frame() -> None:
    """_make_dilated_frame generates valid frames at various times."""
    from python_pkg.praca_magisterska_video._q23_deeplab import _make_dilated_frame
    from python_pkg.praca_magisterska_video._q23_helpers import STEP_DUR, H, W

    frame = _make_dilated_frame(0.0)
    assert frame.shape == (H, W, 3)

    # At time where all 3 grids are visible
    frame2 = _make_dilated_frame(STEP_DUR * 0.9)
    assert frame2.shape == (H, W, 3)

    # Near progress=0 (only first grid)
    frame3 = _make_dilated_frame(STEP_DUR * 0.1)
    assert frame3.shape == (H, W, 3)


def test_make_dilated_frame_progress_breaks() -> None:
    """Test grid visibility at boundary progress values."""
    from python_pkg.praca_magisterska_video._q23_deeplab import _make_dilated_frame
    from python_pkg.praca_magisterska_video._q23_helpers import STEP_DUR

    # progress < 0.3 for gi=1 -> only first grid
    frame = _make_dilated_frame(STEP_DUR * 0.7 * 0.15)
    assert frame is not None

    # progress < 0.6 for gi=2 -> first two grids
    frame2 = _make_dilated_frame(STEP_DUR * 0.7 * 0.45)
    assert frame2 is not None


def test_make_aspp_frame() -> None:
    """_make_aspp_frame generates valid frames."""
    from python_pkg.praca_magisterska_video._q23_deeplab import _make_aspp_frame
    from python_pkg.praca_magisterska_video._q23_helpers import STEP_DUR, H, W

    frame = _make_aspp_frame(0.0)
    assert frame.shape == (H, W, 3)

    # All branches visible
    frame2 = _make_aspp_frame(STEP_DUR * 0.9)
    assert frame2.shape == (H, W, 3)

    # Concat visible but not final_conv
    frame3 = _make_aspp_frame(STEP_DUR * 0.7 * 0.7)
    assert frame3.shape == (H, W, 3)


def test_make_aspp_frame_phases() -> None:
    """Exercise specific phase thresholds in ASPP animation."""
    from python_pkg.praca_magisterska_video._q23_deeplab import _make_aspp_frame
    from python_pkg.praca_magisterska_video._q23_helpers import STEP_DUR

    # Concat phase boundary (progress > 0.6)
    frame = _make_aspp_frame(STEP_DUR * 0.7 * 0.62)
    assert frame is not None

    # Final conv phase (progress > 0.8)
    frame2 = _make_aspp_frame(STEP_DUR * 0.7 * 0.85)
    assert frame2 is not None


def test_deeplab_demo() -> None:
    """_deeplab_demo returns slides."""
    from python_pkg.praca_magisterska_video._q23_deeplab import _deeplab_demo

    slides = _deeplab_demo()
    assert isinstance(slides, list)
    assert len(slides) == 2
