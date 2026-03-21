"""Tests for _q23_classical module."""

from __future__ import annotations


def test_segmentation_concept() -> None:
    """_segmentation_concept returns slides."""
    from python_pkg.praca_magisterska_video._q23_classical import (
        _segmentation_concept,
    )

    slides = _segmentation_concept()
    assert isinstance(slides, list)
    assert len(slides) == 1


def test_thresholding_demo() -> None:
    """_thresholding_demo returns slides with animated threshold."""
    from python_pkg.praca_magisterska_video._q23_classical import (
        _thresholding_demo,
    )

    slides = _thresholding_demo()
    assert isinstance(slides, list)
    assert len(slides) == 1


def test_region_growing_demo() -> None:
    """_region_growing_demo returns slides with animated BFS."""
    from python_pkg.praca_magisterska_video._q23_classical import (
        _region_growing_demo,
    )

    slides = _region_growing_demo()
    assert isinstance(slides, list)
    assert len(slides) == 1


def test_watershed_demo() -> None:
    """_watershed_demo returns slides with flooding animation."""
    from python_pkg.praca_magisterska_video._q23_classical import (
        _watershed_demo,
    )

    slides = _watershed_demo()
    assert isinstance(slides, list)
    assert len(slides) == 1


def test_make_image_frame_directly() -> None:
    """Exercise the make_image_frame closure at different time values."""
    # The frame-generation functions are closures inside the demo functions.
    # They're already exercised by conftest's VideoClip mock,
    # but let's also verify output shape via _segmentation_concept.
    from python_pkg.praca_magisterska_video._q23_classical import (
        _segmentation_concept,
    )

    result = _segmentation_concept()
    assert result is not None


def test_threshold_frame_high_time() -> None:
    """Verify thresholding at high time (threshold near max)."""
    from python_pkg.praca_magisterska_video._q23_classical import (
        _thresholding_demo,
    )

    # VideoClip mock automatically calls make_frame at 0, 0.75*dur, 0.99*dur
    result = _thresholding_demo()
    assert len(result) >= 1


def test_watershed_frame_generation() -> None:
    """Watershed frames exercise dam visibility branches."""
    from python_pkg.praca_magisterska_video._q23_classical import (
        _watershed_demo,
    )

    result = _watershed_demo()
    assert len(result) >= 1


def test_thresholding_small_w() -> None:
    """Exercise thresholding with small W so x+bar_w >= W false branches fire."""
    import python_pkg.praca_magisterska_video._q23_classical as mod

    orig_w = mod.W
    try:
        mod.W = 200
        slides = mod._thresholding_demo()
        assert len(slides) >= 1
    finally:
        mod.W = orig_w


def test_watershed_small_w() -> None:
    """Exercise watershed with small W so fill_top/fill_bot edge branches fire."""
    import python_pkg.praca_magisterska_video._q23_classical as mod

    orig_w, orig_h = mod.W, mod.H
    try:
        mod.W = 150
        mod.H = 200
        slides = mod._watershed_demo()
        assert len(slides) >= 1
    finally:
        mod.W = orig_w
        mod.H = orig_h
