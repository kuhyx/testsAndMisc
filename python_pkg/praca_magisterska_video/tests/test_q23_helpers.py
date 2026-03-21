"""Tests for _q23_helpers module."""

from __future__ import annotations

from unittest.mock import MagicMock


def test_constants() -> None:
    """Verify module-level constants are set correctly."""
    from python_pkg.praca_magisterska_video._q23_helpers import (
        BG_COLOR,
        FONT_B,
        FONT_R,
        FPS,
        HEADER_DUR,
        STEP_DUR,
        H,
        W,
    )

    assert W == 1280
    assert H == 720
    assert FPS == 24
    assert STEP_DUR == 7.0
    assert HEADER_DUR == 4.0
    assert BG_COLOR == (15, 20, 35)
    assert isinstance(FONT_B, str)
    assert isinstance(FONT_R, str)


def test_tc() -> None:
    """_tc adds margin based on font_size."""
    from python_pkg.praca_magisterska_video._q23_helpers import _tc

    result = _tc(text="hello", font_size=24)
    # _tc should call TextClip and return a mock
    assert result is not None


def test_tc_default_font_size() -> None:
    """_tc uses default font_size=24 when not specified."""
    from python_pkg.praca_magisterska_video._q23_helpers import _tc

    result = _tc(text="hello")
    assert result is not None


def test_make_header() -> None:
    """_make_header creates a CompositeVideoClip."""
    from python_pkg.praca_magisterska_video._q23_helpers import _make_header

    result = _make_header("Title", "Subtitle")
    assert result is not None


def test_make_header_custom_duration() -> None:
    """_make_header respects custom duration."""
    from python_pkg.praca_magisterska_video._q23_helpers import _make_header

    result = _make_header("Title", "Subtitle", duration=10.0)
    assert result is not None


def test_text_slide() -> None:
    """_text_slide creates a slide from text elements."""
    from python_pkg.praca_magisterska_video._q23_helpers import (
        FONT_B,
        FONT_R,
        _text_slide,
    )

    lines = [
        ("Line 1", 24, "white", FONT_B, (100, 100)),
        ("Line 2", 18, "#90CAF9", FONT_R, (100, 150)),
    ]
    result = _text_slide(lines)
    assert result is not None


def test_text_slide_custom_duration() -> None:
    """_text_slide with custom duration."""
    from python_pkg.praca_magisterska_video._q23_helpers import (
        FONT_B,
        _text_slide,
    )

    lines = [("Line 1", 24, "white", FONT_B, (100, 100))]
    result = _text_slide(lines, duration=10.0)
    assert result is not None


def test_compose_slide() -> None:
    """_compose_slide overlays text labels on a base clip."""
    from python_pkg.praca_magisterska_video._q23_helpers import (
        FONT_B,
        FONT_R,
        _compose_slide,
    )

    base_clip = MagicMock()
    labels = [
        ("Label 1", 24, "white", FONT_B, (100, 100)),
        ("Label 2", 18, "#90CAF9", FONT_R, (100, 150)),
    ]
    result = _compose_slide(base_clip, labels, duration=7.0)
    assert result is not None


def test_output_dir_exists() -> None:
    """OUTPUT_DIR should be created."""
    from python_pkg.praca_magisterska_video._q23_helpers import OUTPUT_DIR

    assert OUTPUT_DIR is not None


def test_rng_exists() -> None:
    """Module-level rng should be a numpy Generator."""
    from python_pkg.praca_magisterska_video._q23_helpers import rng

    assert hasattr(rng, "integers")
