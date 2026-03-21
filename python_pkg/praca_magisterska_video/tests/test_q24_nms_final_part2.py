"""Tests for _q24_nms_final (part 2): make_frame closure coverage."""

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


_MOD = "python_pkg.praca_magisterska_video._q24_nms_final"


def test_nms_iou_make_frame() -> None:
    """Exercise make_nms_frame at multiple t values to cover all branches."""
    spy, captured = _spy_vc()
    with patch(f"{_MOD}.VideoClip", spy):
        from python_pkg.praca_magisterska_video._q24_nms_final import (
            _nms_iou_demo,
        )

        _nms_iou_demo()

    assert captured
    for mf, dur in captured:
        for t in [0.0, dur * 0.1, dur * 0.3, dur * 0.5, dur * 0.7, dur * 0.99]:
            frame = mf(t)
            assert isinstance(frame, np.ndarray)
            assert frame.shape[2] == 3
