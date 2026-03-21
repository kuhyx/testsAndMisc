"""Tests for _q23_classical (part 2): make_frame closure coverage."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np


def _spy_vc() -> tuple[object, list[tuple[object, float]]]:
    """VideoClip spy capturing make_frame closures."""
    captured: list[tuple[object, float]] = []

    def spy(make_frame=None, duration=None, **_kw: object) -> MagicMock:
        if callable(make_frame):
            captured.append((make_frame, duration or 1.0))
        clip = MagicMock()
        for attr in ("with_fps", "with_duration", "with_position", "with_effects"):
            getattr(clip, attr).return_value = clip
        return clip

    return spy, captured


_MOD = "python_pkg.praca_magisterska_video._q23_classical"


def test_segmentation_concept_make_frame() -> None:
    """Exercise make_image_frame at multiple t values."""
    spy, captured = _spy_vc()
    with patch(f"{_MOD}.VideoClip", spy):
        from python_pkg.praca_magisterska_video._q23_classical import (
            _segmentation_concept,
        )

        _segmentation_concept()

    assert captured
    for mf, dur in captured:
        for t in [0.0, dur * 0.3, dur * 0.6, dur * 0.99]:
            frame = mf(t)
            assert isinstance(frame, np.ndarray)
            assert frame.shape[2] == 3


def test_thresholding_make_frame() -> None:
    """Exercise make_threshold_frame at multiple t values."""
    spy, captured = _spy_vc()
    with patch(f"{_MOD}.VideoClip", spy):
        from python_pkg.praca_magisterska_video._q23_classical import (
            _thresholding_demo,
        )

        _thresholding_demo()

    assert captured
    for mf, dur in captured:
        for t in [0.0, dur * 0.1, dur * 0.5, dur * 0.8, dur * 0.99]:
            frame = mf(t)
            assert isinstance(frame, np.ndarray)


def test_region_growing_make_frame() -> None:
    """Exercise make_region_frame at multiple t values."""
    spy, captured = _spy_vc()
    with patch(f"{_MOD}.VideoClip", spy):
        from python_pkg.praca_magisterska_video._q23_classical import (
            _region_growing_demo,
        )

        _region_growing_demo()

    assert captured
    for mf, dur in captured:
        for t in [0.0, dur * 0.2, dur * 0.5, dur * 0.85, dur * 0.99]:
            frame = mf(t)
            assert isinstance(frame, np.ndarray)


def test_watershed_make_frame() -> None:
    """Exercise make_watershed_frame at multiple t values."""
    spy, captured = _spy_vc()
    with patch(f"{_MOD}.VideoClip", spy):
        from python_pkg.praca_magisterska_video._q23_classical import (
            _watershed_demo,
        )

        _watershed_demo()

    assert captured
    for mf, dur in captured:
        for t in [0.0, dur * 0.3, dur * 0.6, dur * 0.8, dur * 0.99]:
            frame = mf(t)
            assert isinstance(frame, np.ndarray)


def test_thresholding_edge_bar_out_of_range() -> None:
    """Threshold with very small W to hit bar_w >= W branches."""
    import python_pkg.praca_magisterska_video._q23_classical as mod

    spy, captured = _spy_vc()
    orig_w = mod.W
    try:
        mod.W = 150
        with patch(f"{_MOD}.VideoClip", spy):
            mod._thresholding_demo()
        for mf, dur in captured:
            frame = mf(dur * 0.5)
            assert isinstance(frame, np.ndarray)
    finally:
        mod.W = orig_w
