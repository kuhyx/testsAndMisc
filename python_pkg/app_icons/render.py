"""SVG assembly and rasterisation for the shared icon family.

The interesting part here is :func:`centre_offset`. Glyphs are hand-authored, so
their ink never lands exactly on the canvas centre; a barbell is wide and short,
a cloud sits high. Rather than nudging coordinates by hand, the glyph is
rendered once on its own, its ink bounding box is measured, and the whole
fragment is translated so that box is centred. That is what makes a row of
icons line up at the same optical height.

Only the fragment is translated -- never scaled -- so every icon keeps exactly
the family stroke weight.
"""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import TYPE_CHECKING

from python_pkg.app_icons import style

if TYPE_CHECKING:
    from python_pkg.app_icons.glyphs import Glyph


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
    offset: tuple[float, float] = (0.0, 0.0),
) -> str:
    """Assemble a complete SVG document for one icon layer.

    Parameters:
    glyph (Glyph): Artwork to draw.
    accent (str): Hex colour for the glyph, e.g. ``"#26A69A"``.
    with_background (bool): Draw the shared charcoal field behind the glyph.
        False produces the transparent adaptive-icon layers.
    offset (tuple[float, float]): ``(dx, dy)`` translation applied to the
        fragment, normally the result of :func:`centre_offset`.

    Returns:
    str: A standalone SVG document.
    """
    body = glyph.body.replace(style.ACCENT_MARKER, accent)
    dx, dy = offset
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
        f'  <g fill="none" stroke="{accent}" stroke-width="{style.STROKE_WIDTH}" '
        f'stroke-linecap="round" stroke-linejoin="round" '
        f'transform="translate({dx:g},{dy:g})">\n'
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


def _ink_bbox(png: Path) -> tuple[int, int, int, int]:
    """Measure the non-transparent bounding box of a PNG.

    Parameters:
    png (Path): Image to measure.

    Returns:
    tuple[int, int, int, int]: ``(width, height, x, y)`` of the ink box.
    """
    result = subprocess.run(
        [resolve_tool("magick"), str(png), "-trim", "-format", "%w %h %X %Y", "info:"],
        check=True,
        capture_output=True,
        text=True,
    )
    width, height, x, y = result.stdout.split()
    return int(width), int(height), int(x), int(y)


def centre_offset(glyph: Glyph, accent: str) -> tuple[float, float]:
    """Compute the translation that optically centres a glyph.

    The glyph is rendered on a transparent canvas at full resolution, its ink
    box is measured, and the offset from that box's centre to the canvas centre
    is returned.

    Parameters:
    glyph (Glyph): Artwork to measure.
    accent (str): Hex colour to render with. Colour does not affect the box,
        but rsvg-convert needs a concrete value.

    Returns:
    tuple[float, float]: ``(dx, dy)`` to pass to :func:`build_svg`.

    Raises:
    EmptyGlyphError: If the glyph renders no visible ink.
    """
    probe = build_svg(glyph, accent, with_background=False)
    with tempfile.TemporaryDirectory() as tmp:
        png = Path(tmp) / "probe.png"
        rasterise(probe, png, style.CANVAS)
        width, height, x, y = _ink_bbox(png)
    if width == 0 or height == 0:
        raise EmptyGlyphError(glyph.name)
    return style.CENTRE - (x + width / 2), style.CENTRE - (y + height / 2)


def safe_box_overflow(glyph: Glyph, accent: str) -> tuple[int, int]:
    """Measure how far a centred glyph exceeds the adaptive-icon safe box.

    Anything above zero risks being clipped by a launcher mask.

    Parameters:
    glyph (Glyph): Artwork to check.
    accent (str): Hex colour to render with.

    Returns:
    tuple[int, int]: Horizontal and vertical overflow in pixels, clamped at
        zero.
    """
    probe = build_svg(glyph, accent, with_background=False)
    with tempfile.TemporaryDirectory() as tmp:
        png = Path(tmp) / "probe.png"
        rasterise(probe, png, style.CANVAS)
        width, height, _x, _y = _ink_bbox(png)
    return max(0, width - style.SAFE_BOX), max(0, height - style.SAFE_BOX)
