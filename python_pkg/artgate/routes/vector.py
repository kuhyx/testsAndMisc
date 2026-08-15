"""Route (d): code-as-art via SVG, rasterised with ``rsvg-convert``.

SVG is emitted as text and rendered by a system binary, so this route adds no
Python dependency. It is resolution-independent by construction, which is the
property that makes it the natural fit for flat vector/UI work: the same
source renders crisply at any target size.

Gate consequence worth stating: an SVG rasteriser anti-aliases by default, so
output fails ``ALPHA_NOT_BINARY`` unless alpha is explicitly thresholded. That
is a real property of the route, not a defect -- it is why flat-vector output
needs a finishing step before it can be gated as pixel art.
"""

from __future__ import annotations

import shutil
import subprocess
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from pathlib import Path

# Same locked palette as the procedural route, so the two cells are comparable.
PALETTE: Final[dict[str, str]] = {
    "outline": "#1a141c",
    "shadow": "#483c42",
    "mid": "#7c6c68",
    "light": "#c6baaa",
    "gold": "#d6a43e",
    "red": "#b03e3c",
    "cyan": "#5cb0be",
}

_STROKE: Final = 'stroke="#1a141c" stroke-width="1.5" stroke-linejoin="round"'


def _svg(body: str, size: int = 64) -> str:
    """Wrap shape markup in an SVG document.

    Args:
        body: The inner markup.
        size: The viewBox edge length.

    Returns:
        A complete SVG document.
    """
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" '
        f'height="{size}" viewBox="0 0 64 64">{body}</svg>'
    )


SHAPES: Final[dict[str, str]] = {
    "key": (
        f'<circle cx="20" cy="22" r="11" fill="none" stroke="{PALETTE["gold"]}"'
        f' stroke-width="7"/>'
        f'<rect x="27" y="30" width="7" height="27" fill="{PALETTE["gold"]}" '
        f"{_STROKE}/>"
        f'<rect x="34" y="42" width="10" height="5" fill="{PALETTE["gold"]}" '
        f"{_STROKE}/>"
        f'<rect x="34" y="50" width="7" height="5" fill="{PALETTE["gold"]}" '
        f"{_STROKE}/>"
    ),
    "gem": (
        f'<polygon points="32,6 54,26 32,58 10,26" fill="{PALETTE["cyan"]}" '
        f"{_STROKE}/>"
        f'<polygon points="32,6 42,26 32,34 22,26" fill="{PALETTE["light"]}" '
        f'opacity="0.65"/>'
    ),
    "potion": (
        f'<circle cx="32" cy="42" r="17" fill="{PALETTE["cyan"]}" {_STROKE}/>'
        f'<rect x="26" y="12" width="12" height="16" '
        f'fill="{PALETTE["light"]}" {_STROKE}/>'
        f'<rect x="23" y="6" width="18" height="8" fill="{PALETTE["gold"]}" '
        f"{_STROKE}/>"
    ),
    "coin": (
        f'<circle cx="32" cy="32" r="24" fill="{PALETTE["gold"]}" {_STROKE}/>'
        f'<circle cx="32" cy="32" r="18" fill="none" '
        f'stroke="{PALETTE["shadow"]}" stroke-width="2"/>'
        f'<polygon points="32,18 37,29 49,29 39,37 43,49 32,41 21,49 25,37 '
        f'15,29 27,29" fill="{PALETTE["shadow"]}"/>'
    ),
    "shield": (
        f'<path d="M10 10 H54 V32 Q54 52 32 60 Q10 52 10 32 Z" '
        f'fill="{PALETTE["mid"]}" {_STROKE}/>'
        f'<path d="M10 10 H54 V20 H10 Z" fill="{PALETTE["gold"]}"/>'
        f'<circle cx="32" cy="34" r="7" fill="{PALETTE["gold"]}" {_STROKE}/>'
    ),
}


class RenderError(RuntimeError):
    """Raised when the SVG rasteriser is unavailable or fails."""


def render(name: str, out: Path, size: int = 64) -> Path:
    """Rasterise one vector subject to PNG.

    Args:
        name: A key of :data:`SHAPES`.
        out: Destination PNG path.
        size: Output edge length in pixels.

    Returns:
        The written path.

    Raises:
        KeyError: If the subject has no vector shape.
        RenderError: If ``rsvg-convert`` is missing or exits non-zero.
    """
    if name not in SHAPES:
        msg = f"no vector shape for {name!r}"
        raise KeyError(msg)
    binary = shutil.which("rsvg-convert")
    if binary is None:
        msg = "rsvg-convert is not installed"
        raise RenderError(msg)

    source = out.with_suffix(".svg")
    source.write_text(_svg(SHAPES[name], size), encoding="utf-8")
    result = subprocess.run(
        [binary, "-w", str(size), "-h", str(size), str(source), "-o", str(out)],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        msg = f"rsvg-convert failed for {name}: {result.stderr.decode()}"
        raise RenderError(msg)
    return out
