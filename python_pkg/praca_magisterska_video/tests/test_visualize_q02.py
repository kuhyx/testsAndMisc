"""Tests for visualize_q02 module."""

from __future__ import annotations

import numpy as np


def test_constants() -> None:
    """Verify module-level constants."""
    from python_pkg.praca_magisterska_video.visualize_q02 import (
        BG,
        COL_CURRENT,
        COL_DEFAULT,
        COL_EDGE,
        COL_EDGE_ACT,
        COL_VISITED,
        EDGES_BF,
        EDGES_DIJKSTRA,
        FONT_B,
        FONT_R,
        FPS,
        HEADER_DUR,
        INF,
        NODE_POS,
        STEP_DUR,
        H,
        W,
    )

    assert W == 1280
    assert H == 720
    assert FPS == 24
    assert STEP_DUR == 8.0
    assert HEADER_DUR == 5.0
    assert INF == "inf"
    assert len(NODE_POS) == 4
    assert len(EDGES_DIJKSTRA) == 5
    assert len(EDGES_BF) == 4
    assert isinstance(BG, tuple)
    assert isinstance(COL_DEFAULT, tuple)
    assert isinstance(COL_CURRENT, tuple)
    assert isinstance(COL_VISITED, tuple)
    assert isinstance(COL_EDGE, tuple)
    assert isinstance(COL_EDGE_ACT, tuple)
    assert isinstance(FONT_B, str)
    assert isinstance(FONT_R, str)


def test_tc() -> None:
    """_tc adds margin based on font_size."""
    from python_pkg.praca_magisterska_video.visualize_q02 import _tc

    result = _tc(text="hello", font_size=24)
    assert result is not None


def test_make_header() -> None:
    """_make_header creates a title slide."""
    from python_pkg.praca_magisterska_video.visualize_q02 import _make_header

    result = _make_header("Title", "Subtitle")
    assert result is not None


def test_make_header_custom_duration() -> None:
    """_make_header with custom duration."""
    from python_pkg.praca_magisterska_video.visualize_q02 import _make_header

    result = _make_header("Title", "Sub", duration=10.0)
    assert result is not None


def test_draw_circle() -> None:
    """_draw_circle draws a filled circle on a frame."""
    from python_pkg.praca_magisterska_video.visualize_q02 import H, W, _draw_circle

    frame = np.zeros((H, W, 3), dtype=np.uint8)
    _draw_circle(frame, 100, 100, 20, (255, 0, 0))
    assert np.any(frame > 0)


def test_draw_line() -> None:
    """_draw_line draws a line between two points."""
    from python_pkg.praca_magisterska_video.visualize_q02 import H, W, _draw_line

    frame = np.zeros((H, W, 3), dtype=np.uint8)
    _draw_line(frame, (10, 10), (100, 100), (255, 255, 255), thickness=2)
    assert np.any(frame > 0)


def test_draw_arrow() -> None:
    """_draw_arrow draws an arrow between two points."""
    from python_pkg.praca_magisterska_video.visualize_q02 import H, W, _draw_arrow

    frame = np.zeros((H, W, 3), dtype=np.uint8)
    _draw_arrow(frame, (100, 100), (300, 300), (255, 0, 0), thickness=2)
    assert np.any(frame > 0)


def test_render_graph_default() -> None:
    """_render_graph renders a basic graph."""
    from python_pkg.praca_magisterska_video.visualize_q02 import (
        EDGES_DIJKSTRA,
        NODE_POS,
        _render_graph,
    )

    frame = _render_graph(NODE_POS, EDGES_DIJKSTRA, {"S": "0", "A": "inf"})
    assert frame.shape == (720, 1280, 3)


def test_render_graph_with_current_visited() -> None:
    """_render_graph with current node and visited set."""
    from python_pkg.praca_magisterska_video.visualize_q02 import (
        EDGES_DIJKSTRA,
        NODE_POS,
        _render_graph,
    )

    frame = _render_graph(
        NODE_POS,
        EDGES_DIJKSTRA,
        {"S": "0", "A": "2"},
        current="A",
        visited={"S"},
        active_edge=("S", "A"),
    )
    assert frame.shape == (720, 1280, 3)


def test_render_graph_no_active_edge() -> None:
    """_render_graph without active edge."""
    from python_pkg.praca_magisterska_video.visualize_q02 import (
        EDGES_DIJKSTRA,
        NODE_POS,
        _render_graph,
    )

    frame = _render_graph(
        NODE_POS,
        EDGES_DIJKSTRA,
        {"S": "0"},
        current="S",
    )
    assert frame.shape == (720, 1280, 3)


def test_step_config_dataclass() -> None:
    """_StepConfig can be instantiated with defaults."""
    from python_pkg.praca_magisterska_video.visualize_q02 import (
        EDGES_DIJKSTRA,
        NODE_POS,
        _StepConfig,
    )

    cfg = _StepConfig(
        nodes=NODE_POS,
        edges=EDGES_DIJKSTRA,
        distances={"S": "0"},
    )
    assert cfg.current is None
    assert cfg.visited is None
    assert cfg.active_edge is None
    assert cfg.step_text == ""
    assert cfg.algo_name == ""


def test_make_step_minimal() -> None:
    """_make_step creates a CompositeVideoClip from step config."""
    from python_pkg.praca_magisterska_video.visualize_q02 import (
        EDGES_DIJKSTRA,
        NODE_POS,
        _make_step,
        _StepConfig,
    )

    cfg = _StepConfig(
        nodes=NODE_POS,
        edges=EDGES_DIJKSTRA,
        distances={"S": "0", "A": "inf", "B": "inf", "C": "inf"},
    )
    result = _make_step(cfg)
    assert result is not None


def test_make_step_with_all_options() -> None:
    """_make_step with all fields populated."""
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
        step_text="Step description",
        algo_name="Test algo",
    )
    result = _make_step(cfg, duration=5.0)
    assert result is not None


def test_make_step_empty_visited() -> None:
    """_make_step with visited=None defaults to empty set."""
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
        algo_name="Test",
        step_text="desc",
    )
    result = _make_step(cfg)
    assert result is not None


def test_draw_line_out_of_bounds() -> None:
    """_draw_line with edge coords triggers the out-of-bounds branch."""
    import python_pkg.praca_magisterska_video.visualize_q02 as mod

    orig_h, orig_w = mod.H, mod.W
    try:
        mod.H = 30
        mod.W = 30
        frame = np.zeros((30, 30, 3), dtype=np.uint8)
        mod._draw_line(frame, (0, 0), (29, 29), (255, 255, 255), thickness=5)
        assert frame.shape == (30, 30, 3)
    finally:
        mod.H = orig_h
        mod.W = orig_w


def test_main() -> None:
    """main() generates the video without error."""
    from python_pkg.praca_magisterska_video.visualize_q02 import main

    main()
