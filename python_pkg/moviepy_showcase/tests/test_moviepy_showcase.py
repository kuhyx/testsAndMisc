"""Tests for python_pkg.moviepy_showcase.moviepy_showcase."""

from __future__ import annotations

import contextlib
from pathlib import Path
import tempfile
from typing import Any
from unittest.mock import MagicMock, patch

import numpy as np

from python_pkg.moviepy_showcase.moviepy_showcase import (
    H,
    W,
    _base_clip,
    _build,
    _checkerboard,
    _gradient,
    _label,
    _render_part,
    _resize_to_canvas,
    _section_header,
    _titled,
    main,
)
from python_pkg.moviepy_showcase.tests.conftest import create_mock_clip


# ── _gradient ─────────────────────────────────────────────────────
def test_gradient_at_zero() -> None:
    frame = _gradient(0.0)
    assert frame.shape == (H, W, 3)
    assert frame.dtype == np.uint8


def test_gradient_nonzero() -> None:
    frame = _gradient(1.5)
    assert frame.shape == (H, W, 3)


# ── _checkerboard ────────────────────────────────────────────────
def test_checkerboard_at_zero() -> None:
    frame = _checkerboard(0.0)
    assert frame.shape == (H, W, 3)
    assert frame.dtype == np.uint8


def test_checkerboard_nonzero() -> None:
    frame = _checkerboard(2.3)
    assert frame.shape == (H, W, 3)


# ── _base_clip ───────────────────────────────────────────────────
def test_base_clip_default() -> None:
    clip = _base_clip()
    assert clip is not None


def test_base_clip_custom_duration() -> None:
    clip = _base_clip(5.0)
    assert clip is not None


# ── _label ───────────────────────────────────────────────────────
def test_label_defaults() -> None:
    lbl = _label("hello")
    assert lbl is not None


def test_label_custom_params() -> None:
    lbl = _label("hello", size=48, color="red", pos=("left", "top"), dur=3.0)
    assert lbl is not None


# ── _titled ──────────────────────────────────────────────────────
def test_titled() -> None:
    clip = create_mock_clip()
    result = _titled(clip, "test title")
    assert result is not None


# ── _section_header ──────────────────────────────────────────────
def test_section_header_with_subtitle() -> None:
    result = _section_header("Title", "Subtitle text")
    assert result is not None


def test_section_header_without_subtitle() -> None:
    result = _section_header("Title")
    assert result is not None


# ── _resize_to_canvas ───────────────────────────────────────────
def test_resize_to_canvas() -> None:
    clip = create_mock_clip(size=(960, 540))
    result = _resize_to_canvas(clip)
    assert result is not None
    clip.resized.assert_called_once()


# ── _render_part ─────────────────────────────────────────────────
def test_render_part() -> None:
    s1 = create_mock_clip()
    s2 = create_mock_clip()
    _render_part([s1, s2], tempfile.gettempdir() + "/test_part.mp4", "test")
    s1.close.assert_called_once()
    s2.close.assert_called_once()


# ── main ─────────────────────────────────────────────────────────
def test_main_success() -> None:
    mock_dir = tempfile.gettempdir() + "/mock_dir"
    with (
        patch(
            "python_pkg.moviepy_showcase.moviepy_showcase.tempfile.mkdtemp",
            return_value=mock_dir,
        ),
        patch(
            "python_pkg.moviepy_showcase.moviepy_showcase._build",
        ) as mock_build,
        patch(
            "python_pkg.moviepy_showcase.moviepy_showcase.shutil.rmtree",
        ) as mock_rmtree,
    ):
        main()
        mock_build.assert_called_once_with(mock_dir)
        mock_rmtree.assert_called_once_with(mock_dir, ignore_errors=True)


def test_main_build_raises() -> None:
    mock_dir = tempfile.gettempdir() + "/mock_dir"
    with (
        patch(
            "python_pkg.moviepy_showcase.moviepy_showcase.tempfile.mkdtemp",
            return_value=mock_dir,
        ),
        patch(
            "python_pkg.moviepy_showcase.moviepy_showcase._build",
            side_effect=RuntimeError("boom"),
        ),
        patch(
            "python_pkg.moviepy_showcase.moviepy_showcase.shutil.rmtree",
        ) as mock_rmtree,
    ):
        with contextlib.suppress(RuntimeError):
            main()
        mock_rmtree.assert_called_once_with(mock_dir, ignore_errors=True)


# ── _build ───────────────────────────────────────────────────────
def test_build() -> None:
    mock_stat: Any = MagicMock()
    mock_stat.st_size = 10 * 1024 * 1024
    with (
        patch(
            "python_pkg.moviepy_showcase.moviepy_showcase._render_part",
        ),
        patch.object(Path, "stat", return_value=mock_stat),
    ):
        _build(tempfile.gettempdir() + "/test_build")
