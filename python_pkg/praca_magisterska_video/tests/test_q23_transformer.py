"""Tests for _q23_transformer module."""

from __future__ import annotations

import numpy as np


def test_draw_base_grid() -> None:
    """_draw_base_grid fills grid cells."""
    from python_pkg.praca_magisterska_video._q23_helpers import H, W
    from python_pkg.praca_magisterska_video._q23_transformer import _draw_base_grid

    frame = np.zeros((H, W, 3), dtype=np.uint8)
    _draw_base_grid(frame, 60, 200, 6, 40)
    assert np.any(frame > 0)


def test_draw_cnn_kernel_early() -> None:
    """_draw_cnn_kernel does nothing at low progress."""
    from python_pkg.praca_magisterska_video._q23_helpers import H, W
    from python_pkg.praca_magisterska_video._q23_transformer import _draw_cnn_kernel

    frame = np.zeros((H, W, 3), dtype=np.uint8)
    _draw_cnn_kernel(frame, 60, 200, 40, 0.1)
    # At progress <= 0.2, nothing should be drawn
    assert not np.any(frame > 0)


def test_draw_cnn_kernel_active() -> None:
    """_draw_cnn_kernel highlights kernel at sufficient progress."""
    from python_pkg.praca_magisterska_video._q23_helpers import H, W
    from python_pkg.praca_magisterska_video._q23_transformer import _draw_cnn_kernel

    frame = np.zeros((H, W, 3), dtype=np.uint8)
    _draw_cnn_kernel(frame, 60, 200, 40, 0.5)
    assert np.any(frame > 0)


def test_draw_conn_line() -> None:
    """_draw_conn_line draws a dashed line."""
    from python_pkg.praca_magisterska_video._q23_helpers import H, W
    from python_pkg.praca_magisterska_video._q23_transformer import _draw_conn_line

    frame = np.zeros((H, W, 3), dtype=np.uint8)
    _draw_conn_line(frame, 100, 100, 300, 300)
    assert np.any(frame > 0)


def test_draw_conn_line_zero_steps() -> None:
    """_draw_conn_line with same start and end does nothing."""
    from python_pkg.praca_magisterska_video._q23_helpers import H, W
    from python_pkg.praca_magisterska_video._q23_transformer import _draw_conn_line

    frame = np.zeros((H, W, 3), dtype=np.uint8)
    _draw_conn_line(frame, 100, 100, 100, 100)
    assert not np.any(frame > 0)


def test_draw_conn_line_out_of_bounds() -> None:
    """_draw_conn_line with coords beyond frame triggers bounds clipping."""
    from python_pkg.praca_magisterska_video._q23_helpers import H, W
    from python_pkg.praca_magisterska_video._q23_transformer import _draw_conn_line

    frame = np.zeros((H, W, 3), dtype=np.uint8)
    _draw_conn_line(frame, 0, 0, W + 100, H + 100)
    assert frame.shape == (H, W, 3)


def test_draw_attention_connections_early() -> None:
    """_draw_attention_connections does nothing at low progress."""
    from python_pkg.praca_magisterska_video._q23_helpers import H, W
    from python_pkg.praca_magisterska_video._q23_transformer import (
        _draw_attention_connections,
    )

    frame = np.zeros((H, W, 3), dtype=np.uint8)
    _draw_attention_connections(frame, (680, 200), 6, 40, 0.3)
    assert not np.any(frame > 0)


def test_draw_attention_connections_active() -> None:
    """_draw_attention_connections draws at sufficient progress."""
    from python_pkg.praca_magisterska_video._q23_helpers import H, W
    from python_pkg.praca_magisterska_video._q23_transformer import (
        _draw_attention_connections,
    )

    frame = np.zeros((H, W, 3), dtype=np.uint8)
    _draw_attention_connections(frame, (680, 200), 6, 40, 0.9)
    assert np.any(frame > 0)


def test_draw_attention_connections_partial_break() -> None:
    """Trigger the inner-loop break in _draw_attention_connections."""
    from python_pkg.praca_magisterska_video._q23_helpers import H, W
    from python_pkg.praca_magisterska_video._q23_transformer import (
        _draw_attention_connections,
    )

    frame = np.zeros((H, W, 3), dtype=np.uint8)
    # progress=0.6 → n_connections=21, inner loop breaks at conn_idx=22
    _draw_attention_connections(frame, (680, 200), 6, 40, 0.6)
    assert np.any(frame > 0)


def test_make_attention_frame() -> None:
    """_make_attention_frame generates valid frames."""
    from python_pkg.praca_magisterska_video._q23_helpers import STEP_DUR, H, W
    from python_pkg.praca_magisterska_video._q23_transformer import (
        _make_attention_frame,
    )

    frame = _make_attention_frame(0.0)
    assert frame.shape == (H, W, 3)

    frame2 = _make_attention_frame(STEP_DUR * 0.9)
    assert frame2.shape == (H, W, 3)


def test_transformer_seg_demo() -> None:
    """_transformer_seg_demo returns slides."""
    from python_pkg.praca_magisterska_video._q23_transformer import (
        _transformer_seg_demo,
    )

    slides = _transformer_seg_demo()
    assert isinstance(slides, list)
    assert len(slides) >= 3


def test_methods_comparison() -> None:
    """_methods_comparison returns a comparison table slide."""
    from python_pkg.praca_magisterska_video._q23_transformer import (
        _methods_comparison,
    )

    result = _methods_comparison()
    assert result is not None
