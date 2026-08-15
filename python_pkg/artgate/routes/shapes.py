"""Route (a): the twelve subject drawings.

Each shape is given at least one distinguishing FEATURE, because the
`item-icons` measurement found that geometric correctness alone reads as a
placeholder -- a circle with a rim was rejected as "very barebones". The
features here are the fix that finding implies, applied up front.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from python_pkg.artgate.routes.procedural import (
    _blank,
    _disc,
    _put,
    _rect,
    _ring,
    outline,
)

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Callable

    import numpy as np
    from numpy.typing import NDArray


def _key(c: NDArray[np.uint8]) -> None:
    """Draw a key: bow, shaft and two wards."""
    _ring(c, 10.5, 11.5, 5.0, 2.6, "gold")
    _rect(c, 14, 15, 16, 25, "gold")
    _rect(c, 17, 22, 20, 23, "gold")
    _rect(c, 17, 25, 19, 26, "gold")


def _scroll(c: NDArray[np.uint8]) -> None:
    """Draw a scroll: parchment body with rolled ends."""
    _rect(c, 7, 8, 24, 23, "light")
    _rect(c, 6, 6, 25, 9, "mid")
    _rect(c, 6, 22, 25, 25, "mid")
    for y in (12, 15, 18):
        _rect(c, 10, y, 21, y, "shadow")


def _book(c: NDArray[np.uint8]) -> None:
    """Draw a book: cover, spine and a clasp."""
    _rect(c, 6, 6, 25, 26, "red")
    _rect(c, 6, 6, 9, 26, "shadow")
    _rect(c, 11, 9, 23, 10, "light")
    _rect(c, 22, 14, 25, 18, "gold")


def _bone(c: NDArray[np.uint8]) -> None:
    """Draw a bone: shaft with four knobs."""
    _rect(c, 12, 8, 19, 23, "light")
    for cx, cy in ((11, 8), (20, 8), (11, 23), (20, 23)):
        _disc(c, cx, cy, 4.0, "light")
    _rect(c, 14, 12, 15, 19, "mid")


# The gem's widest row; above it the silhouette flares, below it tapers.
_GEM_WAIST = 13


def _gem(c: NDArray[np.uint8]) -> None:
    """Draw a gem: faceted lozenge with a highlight facet."""
    for row in range(6, 27):
        offset = row - _GEM_WAIST
        span = 11 - abs(offset) if offset < 1 else 11 - offset
        if span > 0:
            _rect(c, 16 - span, row, 15 + span, row, "cyan")
    _rect(c, 12, 9, 15, 12, "light")


def _bomb(c: NDArray[np.uint8]) -> None:
    """Draw a bomb: sphere, fuse and a spark."""
    _disc(c, 15.0, 19.0, 9.0, "shadow")
    _disc(c, 12.0, 16.0, 3.0, "mid")
    _rect(c, 16, 6, 17, 10, "mid")
    _rect(c, 18, 4, 19, 6, "gold")
    _put(c, 20, 3, "red")


def _potion(c: NDArray[np.uint8]) -> None:
    """Draw a potion: round flask, neck, stopper and a liquid line."""
    _disc(c, 15.5, 20.0, 8.0, "cyan")
    _rect(c, 13, 7, 18, 13, "light")
    _rect(c, 12, 5, 19, 7, "gold")
    _rect(c, 9, 19, 22, 20, "light")


def _sword(c: NDArray[np.uint8]) -> None:
    """Draw a sword: blade, fuller, crossguard and pommel."""
    _rect(c, 14, 3, 17, 21, "light")
    _rect(c, 15, 5, 16, 19, "mid")
    _rect(c, 9, 22, 22, 23, "gold")
    _rect(c, 14, 24, 17, 27, "shadow")
    _disc(c, 15.5, 28.0, 2.4, "gold")


def _shield(c: NDArray[np.uint8]) -> None:
    """Draw a shield: heater shape with boss and a chevron."""
    _rect(c, 6, 5, 25, 17, "mid")
    for row in range(18, 28):
        inset = row - 17
        _rect(c, 6 + inset, row, 25 - inset, row, "mid")
    _rect(c, 6, 5, 25, 7, "gold")
    _disc(c, 15.5, 15.0, 3.2, "gold")


def _coin(c: NDArray[np.uint8]) -> None:
    """Draw a coin: disc, rim and a struck emblem."""
    _disc(c, 15.5, 15.5, 11.0, "gold")
    _ring(c, 15.5, 15.5, 11.0, 9.0, "shadow")
    _rect(c, 13, 11, 18, 12, "shadow")
    _rect(c, 15, 11, 16, 20, "shadow")


def _ring_item(c: NDArray[np.uint8]) -> None:
    """Draw a ring: band with a raised setting and stone."""
    _ring(c, 15.5, 18.0, 9.0, 6.0, "gold")
    _rect(c, 12, 6, 19, 9, "gold")
    _disc(c, 15.5, 7.0, 3.6, "cyan")
    _put(c, 14, 6, "light")


def _meat(c: NDArray[np.uint8]) -> None:
    """Draw a meat cut: ham body with a protruding bone."""
    _disc(c, 16.0, 19.0, 9.5, "red")
    _disc(c, 12.0, 16.0, 3.0, "gold")
    _rect(c, 14, 4, 17, 11, "light")
    _disc(c, 14.0, 4.0, 2.2, "light")
    _disc(c, 17.5, 4.0, 2.2, "light")


DRAWINGS: Final[dict[str, Callable[[NDArray[np.uint8]], None]]] = {
    "key": _key,
    "scroll": _scroll,
    "book": _book,
    "bone": _bone,
    "gem": _gem,
    "bomb": _bomb,
    "potion": _potion,
    "sword": _sword,
    "shield": _shield,
    "coin": _coin,
    "ring": _ring_item,
    "meat": _meat,
}


def draw(name: str) -> NDArray[np.uint8]:
    """Render one subject as a 32x32 RGBA array.

    Args:
        name: One of the twelve fixed subject names.

    Returns:
        The rendered canvas, outlined.

    Raises:
        KeyError: If the subject has no drawing.
    """
    if name not in DRAWINGS:
        msg = f"no procedural drawing for {name!r}"
        raise KeyError(msg)
    canvas = _blank()
    DRAWINGS[name](canvas)
    outline(canvas)
    return canvas
