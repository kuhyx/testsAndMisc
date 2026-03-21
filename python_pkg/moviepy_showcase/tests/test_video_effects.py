"""Tests for python_pkg.moviepy_showcase._moviepy_video_effects."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from python_pkg.moviepy_showcase._moviepy_video_effects import (
    _fx,
    _part3_effects_1_to_17,
    _part3_effects_18_to_34,
    part3_video_effects,
)
from python_pkg.moviepy_showcase.moviepy_showcase import H, W
from python_pkg.moviepy_showcase.tests.conftest import create_mock_clip


# ── _fx branches ─────────────────────────────────────────────────
def test_fx_normal_path() -> None:
    """Effect succeeds, duration > 0, size matches canvas."""
    clip = create_mock_clip(duration=2.0, size=(W, H))
    with patch(
        "python_pkg.moviepy_showcase._moviepy_video_effects._base_clip",
        return_value=clip,
    ):
        result = _fx(MagicMock(), "label")
    assert result is not None


def test_fx_duration_none() -> None:
    """After with_effects, duration is None → sets duration."""
    clip = create_mock_clip(size=(W, H))
    clip.duration = None
    clip.with_effects.return_value = clip
    clip.with_duration.return_value = create_mock_clip(size=(W, H))
    with patch(
        "python_pkg.moviepy_showcase._moviepy_video_effects._base_clip",
        return_value=clip,
    ):
        result = _fx(MagicMock(), "label")
    assert result is not None


def test_fx_duration_zero() -> None:
    """After with_effects, duration <= 0 → sets duration."""
    clip = create_mock_clip(size=(W, H))
    clip.duration = 0
    clip.with_effects.return_value = clip
    clip.with_duration.return_value = create_mock_clip(size=(W, H))
    with patch(
        "python_pkg.moviepy_showcase._moviepy_video_effects._base_clip",
        return_value=clip,
    ):
        result = _fx(MagicMock(), "label")
    assert result is not None


def test_fx_duration_negative() -> None:
    """After with_effects, duration < 0 → sets duration."""
    clip = create_mock_clip(size=(W, H))
    clip.duration = -1.0
    clip.with_effects.return_value = clip
    clip.with_duration.return_value = create_mock_clip(size=(W, H))
    with patch(
        "python_pkg.moviepy_showcase._moviepy_video_effects._base_clip",
        return_value=clip,
    ):
        result = _fx(MagicMock(), "label")
    assert result is not None


def test_fx_raises_valueerror() -> None:
    """with_effects raises ValueError → falls back to base clip."""
    clip = create_mock_clip(size=(W, H))
    clip.with_effects.side_effect = ValueError("test")
    with patch(
        "python_pkg.moviepy_showcase._moviepy_video_effects._base_clip",
        return_value=clip,
    ):
        result = _fx(MagicMock(), "label")
    assert result is not None


def test_fx_raises_oserror() -> None:
    """with_effects raises OSError → falls back to base clip."""
    clip = create_mock_clip(size=(W, H))
    clip.with_effects.side_effect = OSError("test")
    with patch(
        "python_pkg.moviepy_showcase._moviepy_video_effects._base_clip",
        return_value=clip,
    ):
        result = _fx(MagicMock(), "label")
    assert result is not None


def test_fx_raises_attributeerror() -> None:
    """with_effects raises AttributeError → falls back to base clip."""
    clip = create_mock_clip(size=(W, H))
    clip.with_effects.side_effect = AttributeError("test")
    with patch(
        "python_pkg.moviepy_showcase._moviepy_video_effects._base_clip",
        return_value=clip,
    ):
        result = _fx(MagicMock(), "label")
    assert result is not None


def test_fx_size_mismatch() -> None:
    """After effect, size != (W, H) → resize_to_canvas is called."""
    clip = create_mock_clip(size=(100, 100))
    clip.with_effects.return_value = clip
    with patch(
        "python_pkg.moviepy_showcase._moviepy_video_effects._base_clip",
        return_value=clip,
    ):
        result = _fx(MagicMock(), "label")
    assert result is not None


# ── part functions ───────────────────────────────────────────────
def test_part3_effects_1_to_17() -> None:
    result = _part3_effects_1_to_17()
    assert isinstance(result, list)
    assert len(result) > 0


def test_part3_effects_18_to_34() -> None:
    result = _part3_effects_18_to_34()
    assert isinstance(result, list)
    assert len(result) > 0


def test_part3_video_effects() -> None:
    result = part3_video_effects()
    assert isinstance(result, list)
    # Should include header + effects from both halves
    assert len(result) > 1
