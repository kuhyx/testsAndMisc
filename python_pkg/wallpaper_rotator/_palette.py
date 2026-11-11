"""Dracula-family colours shared by every style (matches the i3bar)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray

Rgb = tuple[int, int, int]

DEEP: Rgb = (0x1A, 0x1B, 0x24)
BG: Rgb = (0x28, 0x2A, 0x36)
LINE: Rgb = (0x44, 0x47, 0x5A)
COMMENT: Rgb = (0x62, 0x72, 0xA4)
CYAN: Rgb = (0x8B, 0xE9, 0xFD)
GREEN: Rgb = (0x50, 0xFA, 0x7B)
ORANGE: Rgb = (0xFF, 0xB8, 0x6C)
PINK: Rgb = (0xFF, 0x79, 0xC6)
PURPLE: Rgb = (0xBD, 0x93, 0xF9)
RED: Rgb = (0xFF, 0x55, 0x55)
ACCENTS: tuple[Rgb, ...] = (CYAN, GREEN, ORANGE, PINK, PURPLE, RED)


def mix(a: Rgb, b: Rgb, t: float) -> Rgb:
    """Linear blend from ``a`` (t=0) to ``b`` (t=1)."""
    return (
        round(a[0] + (b[0] - a[0]) * t),
        round(a[1] + (b[1] - a[1]) * t),
        round(a[2] + (b[2] - a[2]) * t),
    )


def ramp(t: NDArray[np.float64], stops: tuple[Rgb, ...]) -> NDArray[np.uint8]:
    """Map values in [0, 1] through evenly spaced colour stops to RGB."""
    xs = np.linspace(0.0, 1.0, len(stops))
    clipped = np.clip(t, 0.0, 1.0)
    channels = [np.interp(clipped, xs, [stop[c] for stop in stops]) for c in range(3)]
    return np.stack(channels, axis=-1).round().astype(np.uint8)
