"""Tests for the SHAKE-256 seeded streams."""

from __future__ import annotations

from python_pkg.swap_bench.seeded import stream_bytes, stream_u32


def test_streams_are_fixed_by_seed_and_label() -> None:
    """Same seed and label repeat; a different seed or label differs."""
    assert stream_bytes(1, "a", 16) == stream_bytes(1, "a", 16)
    assert stream_bytes(1, "a", 16) != stream_bytes(2, "a", 16)
    assert stream_bytes(1, "a", 16) != stream_bytes(1, "b", 16)


def test_u32_stream_length_and_range() -> None:
    """``stream_u32`` returns n values below 2**32."""
    values = stream_u32(3, "x", 100)
    assert len(values) == 100
    assert all(0 <= v < 1 << 32 for v in values)
    assert len(set(values)) > 90
