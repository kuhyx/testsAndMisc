"""Route (a): procedural/parametric icon generation.

Draws the fixed subject set as 32x32 pixel art from a locked palette using
plain geometry -- no model, no randomness beyond a seed, fully deterministic
and CPU-only.

The honest expectation, from `item-icons`: geometry reliably reaches "not
wrong" and does not reach "good". Plain primitives (coin, ring, shield) are
predicted to read as placeholders no matter how correct the circle is, which
is why every shape here is given at least one distinguishing feature.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

import numpy as np

from python_pkg.artgate.pixels import OPAQUE

if TYPE_CHECKING:  # pragma: no cover
    from numpy.typing import NDArray

SIZE: Final = 32

# A compact ramp: dark outline, two mid tones, a highlight and three accents.
# Kept small deliberately -- the corpus median for real 32x32 icons is 8.
PALETTE: Final[dict[str, tuple[int, int, int]]] = {
    "outline": (26, 20, 28),
    "shadow": (72, 60, 66),
    "mid": (124, 108, 104),
    "light": (198, 186, 170),
    "gold": (214, 164, 62),
    "red": (176, 62, 60),
    "cyan": (92, 176, 190),
}


def _blank() -> NDArray[np.uint8]:
    """Return a fully transparent 32x32 RGBA canvas.

    Returns:
        An ``(SIZE, SIZE, 4)`` uint8 array.
    """
    return np.zeros((SIZE, SIZE, 4), dtype=np.uint8)


def _put(canvas: NDArray[np.uint8], x: int, y: int, colour: str) -> None:
    """Paint one opaque pixel, ignoring out-of-bounds writes.

    Args:
        canvas: The target canvas.
        x: Column.
        y: Row.
        colour: A key of :data:`PALETTE`.
    """
    if 0 <= x < SIZE and 0 <= y < SIZE:
        canvas[y, x, :3] = PALETTE[colour]
        canvas[y, x, 3] = OPAQUE


def _rect(
    canvas: NDArray[np.uint8],
    x0: int,
    y0: int,
    x1: int,
    y1: int,
    colour: str,
) -> None:
    """Fill an inclusive rectangle.

    Args:
        canvas: The target canvas.
        x0: Left column.
        y0: Top row.
        x1: Right column, inclusive.
        y1: Bottom row, inclusive.
        colour: A key of :data:`PALETTE`.
    """
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            _put(canvas, x, y, colour)


def _disc(
    canvas: NDArray[np.uint8],
    cx: float,
    cy: float,
    radius: float,
    colour: str,
) -> None:
    """Fill a filled circle using a squared-distance test.

    Args:
        canvas: The target canvas.
        cx: Centre column.
        cy: Centre row.
        radius: Radius in pixels.
        colour: A key of :data:`PALETTE`.
    """
    limit = radius * radius
    for y in range(SIZE):
        for x in range(SIZE):
            if (x - cx) ** 2 + (y - cy) ** 2 <= limit:
                _put(canvas, x, y, colour)


def _ring(
    canvas: NDArray[np.uint8],
    cx: float,
    cy: float,
    outer: float,
    inner: float,
    colour: str,
) -> None:
    """Fill an annulus.

    Args:
        canvas: The target canvas.
        cx: Centre column.
        cy: Centre row.
        outer: Outer radius.
        inner: Inner radius.
        colour: A key of :data:`PALETTE`.
    """
    hi, lo = outer * outer, inner * inner
    for y in range(SIZE):
        for x in range(SIZE):
            dist = (x - cx) ** 2 + (y - cy) ** 2
            if lo <= dist <= hi:
                _put(canvas, x, y, colour)


def outline(canvas: NDArray[np.uint8]) -> None:
    """Trace a one-pixel dark border around every opaque region.

    A consistent outline is what makes a small sprite read against arbitrary
    backgrounds; it is also what the silhouette gate rewards.

    Args:
        canvas: The canvas to outline in place.
    """
    solid = canvas[:, :, 3] == OPAQUE
    pad = np.pad(solid, 1, constant_values=False)
    neighbours = pad[:-2, 1:-1] | pad[2:, 1:-1] | pad[1:-1, :-2] | pad[1:-1, 2:]
    edge = (~solid) & neighbours
    canvas[edge, :3] = PALETTE["outline"]
    canvas[edge, 3] = OPAQUE
