"""Tests for python_pkg.moviepy_showcase._moviepy_audio_output."""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np

from python_pkg.moviepy_showcase._moviepy_audio_output import (
    _make_sine,
    part4_audio,
    part5_composition,
    part6_drawing_tools,
    part7_output,
)


# ── _make_sine inner maker branches ──────────────────────────────
def test_make_sine_returns_clip() -> None:
    clip = _make_sine(440.0, 2.0)
    assert clip is not None


def test_make_sine_maker_scalar() -> None:
    """maker() with scalar t → t_arr.ndim == 0 → returns 1-D."""
    import moviepy as mp

    mp.AudioClip.side_effect = lambda *a, **kw: MagicMock()
    _make_sine(440.0, 1.0)
    maker = mp.AudioClip.call_args[0][0]

    result = maker(0.0)
    assert isinstance(result, np.ndarray)
    assert result.ndim == 1
    assert result.shape == (2,)


def test_make_sine_maker_array() -> None:
    """maker() with array t → t_arr.ndim > 0 → returns 2-D."""
    import moviepy as mp

    mp.AudioClip.side_effect = lambda *a, **kw: MagicMock()
    _make_sine(440.0, 1.0)
    maker = mp.AudioClip.call_args[0][0]

    t = np.linspace(0, 1, 100)
    result = maker(t)
    assert isinstance(result, np.ndarray)
    assert result.ndim == 2
    assert result.shape == (100, 2)


# ── part functions ───────────────────────────────────────────────
def test_part4_audio() -> None:
    result = part4_audio()
    assert isinstance(result, list)
    assert len(result) > 0


def test_part5_composition() -> None:
    result = part5_composition()
    assert isinstance(result, list)
    assert len(result) > 0


def test_part6_drawing_tools() -> None:
    result = part6_drawing_tools()
    assert isinstance(result, list)
    assert len(result) > 0


def test_part7_output() -> None:
    result = part7_output()
    assert isinstance(result, list)
    assert len(result) > 0
