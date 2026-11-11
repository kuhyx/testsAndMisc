"""Style 1: a dark diagonal gradient with film grain."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from PIL import Image

from python_pkg.wallpaper_rotator import _palette

if TYPE_CHECKING:
    from python_pkg.wallpaper_rotator._context import RenderContext

_GRAIN = 3


def render(
    _ctx: RenderContext, size: tuple[int, int], rng: np.random.Generator
) -> Image.Image:
    """Blend BG into DEEP along a random diagonal, then add faint noise."""
    width, height = size
    angle = rng.uniform(0.0, 2.0 * np.pi)
    # The ramp is smooth: compute it at a quarter size, then upscale.
    small_w, small_h = max(width // 4, 2), max(height // 4, 2)
    ys, xs = np.indices((small_h, small_w), dtype=np.float64)
    proj = xs / small_w * np.cos(angle) + ys / small_h * np.sin(angle)
    t = (proj - proj.min()) / max(float(np.ptp(proj)), 1e-9)
    small = Image.fromarray(_palette.ramp(t, (_palette.BG, _palette.DEEP)), "RGB")
    base = np.asarray(small.resize(size, Image.Resampling.BICUBIC), dtype=np.int16)
    grain = rng.integers(-_GRAIN, _GRAIN + 1, size=(height, width, 1), dtype=np.int16)
    return Image.fromarray(np.clip(base + grain, 0, 255).astype(np.uint8), "RGB")
