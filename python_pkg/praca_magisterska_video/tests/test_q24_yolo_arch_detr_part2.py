"""Tests for _q24_yolo_arch_detr (part 2): make_frame closure coverage."""

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


_MOD = "python_pkg.praca_magisterska_video._q24_yolo_arch_detr"


def test_yolo_architecture_make_frame() -> None:
    """Exercise make_yolo_arch at multiple t values."""
    spy, captured = _spy_vc()
    with patch(f"{_MOD}.VideoClip", spy):
        from python_pkg.praca_magisterska_video._q24_yolo_arch_detr import (
            _yolo_architecture,
        )

        _yolo_architecture()

    assert captured
    for mf, dur in captured:
        for t in [
            0.0,
            dur * 0.1,
            dur * 0.3,
            dur * 0.5,
            dur * 0.65,
            dur * 0.8,
            dur * 0.99,
        ]:
            frame = mf(t)
            assert isinstance(frame, np.ndarray)
            assert frame.shape[2] == 3


def test_detr_make_frame() -> None:
    """Exercise make_detr_frame at multiple t values."""
    spy, captured = _spy_vc()
    with patch(f"{_MOD}.VideoClip", spy):
        from python_pkg.praca_magisterska_video._q24_yolo_arch_detr import (
            _detr_demo,
        )

        _detr_demo()

    assert captured
    for mf, dur in captured:
        for t in [0.0, dur * 0.1, dur * 0.3, dur * 0.55, dur * 0.8, dur * 0.99]:
            frame = mf(t)
            assert isinstance(frame, np.ndarray)
