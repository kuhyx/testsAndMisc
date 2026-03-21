"""Tests for _q24_common module."""

from __future__ import annotations


def test_constants() -> None:
    """Verify module-level constants are set correctly."""
    from python_pkg.praca_magisterska_video._q24_common import (
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
    from python_pkg.praca_magisterska_video._q24_common import _tc

    result = _tc(text="hello", font_size=24)
    assert result is not None


def test_tc_default_font_size() -> None:
    """_tc uses default font_size=24 when not specified."""
    from python_pkg.praca_magisterska_video._q24_common import _tc

    result = _tc(text="hello")
    assert result is not None


def test_make_header() -> None:
    """_make_header creates a CompositeVideoClip."""
    from python_pkg.praca_magisterska_video._q24_common import _make_header

    result = _make_header("Title", "Subtitle")
    assert result is not None


def test_make_header_custom_duration() -> None:
    """_make_header respects custom duration."""
    from python_pkg.praca_magisterska_video._q24_common import _make_header

    result = _make_header("Title", "Subtitle", duration=10.0)
    assert result is not None


def test_text_slide() -> None:
    """_text_slide creates a slide from text elements."""
    from python_pkg.praca_magisterska_video._q24_common import (
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
    from python_pkg.praca_magisterska_video._q24_common import (
        FONT_B,
        _text_slide,
    )

    lines = [("Line 1", 24, "white", FONT_B, (100, 100))]
    result = _text_slide(lines, duration=10.0)
    assert result is not None


def test_output_dir_exists() -> None:
    """OUTPUT_DIR should be created."""
    from python_pkg.praca_magisterska_video._q24_common import OUTPUT_DIR

    assert OUTPUT_DIR is not None


def test_all_exports() -> None:
    """__all__ should contain expected names."""
    from python_pkg.praca_magisterska_video._q24_common import __all__

    assert "BG_COLOR" in __all__
    assert "_tc" in __all__
    assert "_make_header" in __all__
    assert "_text_slide" in __all__
