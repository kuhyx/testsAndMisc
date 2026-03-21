"""Tests for python_pkg.moviepy_showcase._moviepy_clip_types."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np

from python_pkg.moviepy_showcase._moviepy_clip_types import (
    part1_clip_types,
    part2_clip_methods,
)
from python_pkg.moviepy_showcase.moviepy_showcase import H, W
from python_pkg.moviepy_showcase.tests.conftest import create_mock_clip


# ── part1_clip_types ─────────────────────────────────────────────
def test_part1_clip_types_returns_scenes() -> None:
    result = part1_clip_types()
    assert isinstance(result, list)
    assert len(result) > 0


def test_part1_data_to_frame() -> None:
    """Extract and test the inner data_to_frame function."""
    import moviepy as mp

    mp.DataVideoClip.side_effect = lambda *a, **kw: create_mock_clip()
    result = part1_clip_types()
    assert len(result) > 0

    # DataVideoClip is called with (data_list, data_to_frame, fps=FPS)
    for call in mp.DataVideoClip.call_args_list:
        if len(call[0]) >= 2 and callable(call[0][1]):
            data_to_frame = call[0][1]
            frame = data_to_frame(30)
            assert frame.shape == (H, W, 3)
            assert frame.dtype == np.uint8
            # Test with 0 (edge case: bar_w = 0)
            frame0 = data_to_frame(0)
            assert frame0.shape == (H, W, 3)
            break


# ── part2_clip_methods ───────────────────────────────────────────
def test_part2_clip_methods_returns_scenes() -> None:
    result = part2_clip_methods()
    assert isinstance(result, list)
    assert len(result) > 0


def test_part2_flip_lr() -> None:
    """Extract and test the inner flip_lr function."""
    base_mock = create_mock_clip()
    with patch(
        "python_pkg.moviepy_showcase._moviepy_clip_types._base_clip",
        return_value=base_mock,
    ):
        part2_clip_methods()

    # flip_lr was passed to image_transform
    flip_lr = base_mock.image_transform.call_args[0][0]
    img = np.arange(24, dtype=np.uint8).reshape(2, 4, 3)
    flipped = flip_lr(img)
    np.testing.assert_array_equal(flipped, img[:, ::-1])


def test_part2_shift_right() -> None:
    """Extract and test the inner shift_right function."""
    base_mock = create_mock_clip()
    with patch(
        "python_pkg.moviepy_showcase._moviepy_clip_types._base_clip",
        return_value=base_mock,
    ):
        part2_clip_methods()

    # shift_right was passed to transform
    shift_right = base_mock.transform.call_args[0][0]
    dummy_frame = np.ones((4, 6, 3), dtype=np.uint8)
    gf = MagicMock(return_value=dummy_frame)
    result = shift_right(gf, 1.0)
    gf.assert_called_once_with(1.0)
    assert result.shape == dummy_frame.shape
