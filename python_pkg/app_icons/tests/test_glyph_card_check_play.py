"""Tests for the todo_implementer glyph (board card, tick, play arrow)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from PIL import Image

from python_pkg.app_icons import apps, fit, glyphs, labels, render, style

if TYPE_CHECKING:
    from pathlib import Path


def _row_gaps(y: int, tmp_path: Path) -> list[int]:
    """Transparent runs between inked runs along row ``y`` at the final scale."""
    glyph = glyphs.get_glyph("card-check-play")
    placement = fit.placement(glyph, "#FFFFFF")
    png = tmp_path / "card.png"
    svg = render.build_svg(glyph, "#FFFFFF", with_background=False, offset=placement)
    render.rasterise(svg, png, style.CANVAS)
    with Image.open(png) as image:
        alpha = np.asarray(image.convert("RGBA"))[y, :, 3]
    edges = np.flatnonzero(np.diff((alpha > 127).astype(np.int8)))
    ends, starts = edges[1::2], edges[2::2]
    return [int(start - end) for end, start in zip(ends, starts, strict=False)]


def test_todo_implementer_uses_it() -> None:
    app = apps.get_app("todo_implementer")
    assert app.glyph == "card-check-play"
    assert app.linux
    assert labels.LABELS["todo_implementer"] == "TodoImpl"


def test_negative_space_at_final_scale(tmp_path: Path) -> None:
    """Card edge -> tick -> play -> card edge across the middle: none merge."""
    best: list[int] = []
    for y in range(int(style.CENTRE) - 80, int(style.CENTRE) + 81, 8):
        gaps = _row_gaps(y, tmp_path)
        if len(gaps) == 3:
            best = gaps
            assert min(gaps) >= style.MIN_NEGATIVE_SPACE, (y, gaps)
    assert best, "no row crosses card, tick, play and card"
