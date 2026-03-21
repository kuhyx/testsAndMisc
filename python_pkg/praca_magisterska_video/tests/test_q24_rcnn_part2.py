"""Tests for _q24_rcnn (part 2): make_frame closure coverage."""

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


_MOD = "python_pkg.praca_magisterska_video._q24_rcnn"


def test_rcnn_evolution_make_frame() -> None:
    """Exercise make_evolution_frame at multiple t values."""
    spy, captured = _spy_vc()
    with patch(f"{_MOD}.VideoClip", spy):
        from python_pkg.praca_magisterska_video._q24_rcnn import (
            _rcnn_evolution,
        )

        _rcnn_evolution()

    assert captured
    for mf, dur in captured:
        for t in [0.0, dur * 0.1, dur * 0.3, dur * 0.5, dur * 0.8, dur * 0.99]:
            frame = mf(t)
            assert isinstance(frame, np.ndarray)
            assert frame.shape[2] == 3


def test_rcnn_detailed_make_frame() -> None:
    """Exercise make_rcnn_pipeline at multiple t values."""
    spy, captured = _spy_vc()
    with patch(f"{_MOD}.VideoClip", spy):
        from python_pkg.praca_magisterska_video._q24_rcnn import (
            _rcnn_detailed,
        )

        _rcnn_detailed()

    assert captured
    for mf, dur in captured:
        for t in [0.0, dur * 0.1, dur * 0.25, dur * 0.5, dur * 0.8, dur * 0.99]:
            frame = mf(t)
            assert isinstance(frame, np.ndarray)
