"""Tests for _q24_rpn_yolo (part 2): make_frame closure coverage."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import numpy as np

if TYPE_CHECKING:
    from collections.abc import Callable


def _spy_vc() -> tuple[object, list[tuple[object, float]]]:
    """VideoClip spy capturing make_frame closures."""
    captured: list[tuple[object, float]] = []

    def spy(
        make_frame: Callable[[float], np.ndarray] | None = None,
        duration: float | None = None,
        **_kw: object,
    ) -> MagicMock:
        if callable(make_frame):
            captured.append((make_frame, duration or 1.0))
        clip = MagicMock()
        for attr in ("with_fps", "with_duration", "with_position", "with_effects"):
            getattr(clip, attr).return_value = clip
        return clip

    return spy, captured


_MOD = "python_pkg.praca_magisterska_video._q24_rpn_yolo"


def test_rpn_anchors_make_frame() -> None:
    """Exercise make_anchors_frame at multiple t values."""
    spy, captured = _spy_vc()
    with patch(f"{_MOD}.VideoClip", spy):
        from python_pkg.praca_magisterska_video._q24_rpn_yolo import (
            _rpn_anchors_demo,
        )

        _rpn_anchors_demo()

    assert captured
    for mf, dur in captured:
        for t in [0.0, dur * 0.05, dur * 0.2, dur * 0.5, dur * 0.8, dur * 0.99]:
            frame = mf(t)
            assert isinstance(frame, np.ndarray)
            assert frame.shape[2] == 3


def test_yolo_make_frame() -> None:
    """Exercise make_yolo_frame at multiple t values."""
    spy, captured = _spy_vc()
    with patch(f"{_MOD}.VideoClip", spy):
        from python_pkg.praca_magisterska_video._q24_rpn_yolo import (
            _yolo_demo,
        )

        _yolo_demo()

    assert captured
    for mf, dur in captured:
        for t in [0.0, dur * 0.1, dur * 0.35, dur * 0.55, dur * 0.7, dur * 0.99]:
            frame = mf(t)
            assert isinstance(frame, np.ndarray)
