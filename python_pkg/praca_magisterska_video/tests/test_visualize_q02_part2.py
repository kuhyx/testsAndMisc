"""Tests for visualize_q02 (part 2): step_text branch coverage."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np


def test_make_step_step_text_branch() -> None:
    """_make_step with step_text exercises the step_text overlay branch."""
    from python_pkg.praca_magisterska_video.visualize_q02 import (
        EDGES_DIJKSTRA,
        NODE_POS,
        _make_step,
        _StepConfig,
    )

    cfg = _StepConfig(
        nodes=NODE_POS,
        edges=EDGES_DIJKSTRA,
        distances={"S": "0", "A": "2", "B": "5", "C": "inf"},
        current="A",
        visited={"S"},
        active_edge=("S", "A"),
        step_text="Relaxing edge S→A, new dist(A) = 2",
        algo_name="Dijkstra",
    )
    result = _make_step(cfg, duration=3.0)
    assert result is not None


def test_make_step_no_step_text() -> None:
    """_make_step with empty step_text skips the overlay branch."""
    from python_pkg.praca_magisterska_video.visualize_q02 import (
        EDGES_DIJKSTRA,
        NODE_POS,
        _make_step,
        _StepConfig,
    )

    cfg = _StepConfig(
        nodes=NODE_POS,
        edges=EDGES_DIJKSTRA,
        distances={"S": "0"},
        step_text="",
    )
    result = _make_step(cfg)
    assert result is not None


def test_make_frame_closure_returns_ndarray() -> None:
    """Line 222: exercise graph_frame.copy() inside the make_frame closure."""
    from python_pkg.praca_magisterska_video.visualize_q02 import (
        EDGES_DIJKSTRA,
        NODE_POS,
        _make_step,
        _StepConfig,
    )

    captured: list[object] = []

    def capturing_video_clip(make_frame: object = None, **kw: object) -> MagicMock:
        captured.append(make_frame)
        clip = MagicMock()
        clip.with_fps.return_value = clip
        return clip

    cfg = _StepConfig(
        nodes=NODE_POS,
        edges=EDGES_DIJKSTRA,
        distances={"S": "0"},
        step_text="",
    )
    with patch(
        "python_pkg.praca_magisterska_video.visualize_q02.VideoClip",
        capturing_video_clip,
    ):
        _make_step(cfg)

    assert captured
    make_frame_fn = captured[0]
    assert callable(make_frame_fn)
    frame = make_frame_fn(0.0)
    assert isinstance(frame, np.ndarray)
