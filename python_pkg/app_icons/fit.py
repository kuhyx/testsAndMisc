"""Fit every glyph to the same circle: centred, with ink radius ``INK_RADIUS``.

Hand-authored glyphs span anything from 250 to 400px, so a row of icons looked
like different sizes (kuhy, 2026-10-23). Each glyph is rendered, its ink is
measured, and a :class:`~python_pkg.app_icons.render.Placement` is derived that
centres the ink box and scales it so the furthest inked pixel sits exactly
``style.INK_RADIUS`` from the centre.

The stroke weight does not scale with the glyph (see :func:`render.build_svg`),
so the radius is not linear in the scale; a few measure-and-correct rounds
converge well inside the tolerance.
"""

from __future__ import annotations

from pathlib import Path
import tempfile
from typing import TYPE_CHECKING, Final

import numpy as np
from PIL import Image

from python_pkg.app_icons import render, style

if TYPE_CHECKING:
    from python_pkg.app_icons.glyphs import Glyph

# Alpha above this counts as ink; the anti-aliased fringe below it does not.
_INK_ALPHA: Final[int] = 127
_MAX_ROUNDS: Final[int] = 8
_TOLERANCE: Final[float] = 0.002


def ink_geometry(png: Path) -> tuple[float, float, float]:
    """Measure a rendered glyph.

    Parameters:
    png (Path): Transparent render of the glyph alone.

    Returns:
    tuple[float, float, float]: ``(radius, cx, cy)`` -- the ink box centre and
        the distance from it to the furthest inked pixel. All zero for no ink.
    """
    with Image.open(png) as image:
        alpha = np.asarray(image.convert("RGBA"))[:, :, 3]
    ys, xs = np.nonzero(alpha > _INK_ALPHA)
    if xs.size == 0:
        return 0.0, 0.0, 0.0
    cx = (int(xs.min()) + int(xs.max()) + 1) / 2
    cy = (int(ys.min()) + int(ys.max()) + 1) / 2
    radius = float(np.hypot(xs + 0.5 - cx, ys + 0.5 - cy).max())
    return radius, cx, cy


def _measure(
    glyph: Glyph, accent: str, where: render.Placement
) -> tuple[float, float, float]:
    """Render ``glyph`` at ``where`` and measure its ink."""
    svg = render.build_svg(glyph, accent, with_background=False, offset=where)
    with tempfile.TemporaryDirectory() as tmp:
        png = Path(tmp) / "probe.png"
        render.rasterise(svg, png, style.CANVAS)
        return ink_geometry(png)


def placement(glyph: Glyph, accent: str) -> render.Placement:
    """Find the placement that centres a glyph on the family ink circle.

    Parameters:
    glyph (Glyph): Artwork to fit.
    accent (str): Hex colour to render with; it does not affect the result,
        but rsvg-convert needs a concrete value.

    Returns:
    render.Placement: Transform to pass to :func:`render.build_svg`.

    Raises:
    render.EmptyGlyphError: If the glyph renders no visible ink.
    """
    where = render.IDENTITY
    for _ in range(_MAX_ROUNDS):
        radius, cx, cy = _measure(glyph, accent, where)
        if radius == 0:
            raise render.EmptyGlyphError(glyph.name)
        factor = style.INK_RADIUS / radius
        # Move the ink centre onto the canvas centre, then scale about it:
        # p -> C + factor * (scale*p + d - c).
        where = render.Placement(
            dx=style.CENTRE + factor * (where.dx - cx),
            dy=style.CENTRE + factor * (where.dy - cy),
            scale=where.scale * factor,
        )
        if abs(factor - 1) <= _TOLERANCE:
            break
    return where
