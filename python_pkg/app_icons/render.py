"""SVG assembly and rasterisation for the shared icon family.

Glyphs are hand-authored, so their ink never lands on the canvas centre and
never spans the same circle. :mod:`python_pkg.app_icons.fit` measures each one
and returns a :class:`Placement`; :func:`build_svg` applies it. The fragment is
translated and scaled, but the group's stroke width is divided by the scale,
so every stroked icon keeps exactly the family stroke weight. A fragment with
its own inner ``scale(k)`` writes ``stroke-width="{{STROKE/k}}"`` and gets the
same compensation. Filled shapes have no stroke and simply scale.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
import shutil
import subprocess
from typing import TYPE_CHECKING

from python_pkg.app_icons import style

if TYPE_CHECKING:
    from pathlib import Path

    from python_pkg.app_icons.glyphs import Glyph


# ``{{STROKE/k}}``: the family stroke weight inside a group already scaled by k.
_STROKE_MARKER = re.compile(r"\{\{STROKE/(\d+(?:\.\d+)?)\}\}")


@dataclass(frozen=True)
class Placement:
    """Where a glyph fragment lands: ``translate(dx, dy) scale(scale)``.

    Parameters:
    dx (float): Horizontal translation in canvas pixels.
    dy (float): Vertical translation in canvas pixels.
    scale (float): Uniform scale applied after the translation.
    """

    dx: float = 0.0
    dy: float = 0.0
    scale: float = 1.0


IDENTITY = Placement()


class ToolMissingError(RuntimeError):
    """Raised when a required external rasterisation tool is not installed."""

    def __init__(self, tool: str) -> None:
        """Record which tool was missing.

        Parameters:
        tool (str): Executable name that could not be found on PATH.
        """
        super().__init__(f"required tool {tool!r} is not installed")
        self.tool = tool


class EmptyGlyphError(ValueError):
    """Raised when a glyph renders to nothing, so it cannot be centred."""

    def __init__(self, name: str) -> None:
        """Record which glyph produced no ink.

        Parameters:
        name (str): Glyph identifier that rendered empty.
        """
        super().__init__(f"glyph {name!r} rendered no visible ink")
        self.name = name


def resolve_tool(name: str) -> str:
    """Resolve an external tool to an absolute path.

    Parameters:
    name (str): Executable name, e.g. ``"rsvg-convert"``.

    Returns:
    str: Absolute path to the executable.

    Raises:
    ToolMissingError: If the executable is not on PATH.
    """
    resolved = shutil.which(name)
    if resolved is None:
        raise ToolMissingError(name)
    return resolved


def build_svg(
    glyph: Glyph,
    accent: str,
    *,
    with_background: bool,
    offset: Placement = IDENTITY,
) -> str:
    """Assemble a complete SVG document for one icon layer.

    Parameters:
    glyph (Glyph): Artwork to draw.
    accent (str): Hex colour for the glyph, e.g. ``"#26A69A"``.
    with_background (bool): Draw the shared charcoal field behind the glyph.
        False produces the transparent adaptive-icon layers.
    offset (Placement): Transform applied to the fragment, normally the
        result of :func:`python_pkg.app_icons.fit.placement`.

    Returns:
    str: A standalone SVG document.
    """
    body = glyph.body.replace(style.ACCENT_MARKER, accent)
    body = _STROKE_MARKER.sub(
        lambda m: f"{style.STROKE_WIDTH / (offset.scale * float(m[1])):g}", body
    )
    stroke = style.STROKE_WIDTH / offset.scale
    field = (
        f'\n  <rect width="{style.CANVAS}" height="{style.CANVAS}" '
        f'fill="{style.BACKGROUND}"/>'
        if with_background
        else ""
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{style.CANVAS}" '
        f'height="{style.CANVAS}" viewBox="0 0 {style.CANVAS} {style.CANVAS}">'
        f"{field}\n"
        f'  <g fill="none" stroke="{accent}" stroke-width="{stroke:g}" '
        f'stroke-linecap="round" stroke-linejoin="round" '
        f'transform="translate({offset.dx:g},{offset.dy:g}) '
        f'scale({offset.scale:g})">\n'
        f"{body}\n"
        f"  </g>\n"
        f"</svg>\n"
    )


def rasterise(svg_text: str, destination: Path, size: int) -> None:
    """Render an SVG document to a square PNG.

    Parameters:
    svg_text (str): Complete SVG document.
    destination (Path): PNG path to write; parent directories are created.
    size (int): Output width and height in pixels.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            resolve_tool("rsvg-convert"),
            "-w",
            str(size),
            "-h",
            str(size),
            "-o",
            str(destination),
        ],
        input=svg_text.encode(),
        check=True,
        capture_output=True,
    )
