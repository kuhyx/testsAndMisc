"""Style 6: a frozen frame of a slow plasma shader, in dark palette tones."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from PIL import Image

from python_pkg.wallpaper_rotator import _palette

if TYPE_CHECKING:
    from python_pkg.wallpaper_rotator._context import RenderContext

# Smooth field: render at a quarter and upscale, a 16x cheaper pass.
_DOWNSCALE = 4
_WAVES = 4


def render(
    _ctx: RenderContext, size: tuple[int, int], rng: np.random.Generator
) -> Image.Image:
    """Sum random sine waves, map through a dark ramp with one dim accent."""
    width, height = size
    small_w, small_h = max(width // _DOWNSCALE, 2), max(height // _DOWNSCALE, 2)
    ys, xs = np.indices((small_h, small_w), dtype=np.float64)
    xs /= small_w
    ys /= small_h
    field = np.zeros_like(xs)
    for _ in range(_WAVES):
        fx, fy = rng.uniform(1.0, 6.0, size=2)
        phase = rng.uniform(0.0, 2.0 * np.pi)
        field += np.sin(xs * fx * 2 * np.pi + ys * fy * 2 * np.pi + phase)
    cx, cy = rng.uniform(0.2, 0.8, size=2)
    field += np.sin(np.hypot(xs - cx, ys - cy) * rng.uniform(6.0, 14.0))
    t = (field - field.min()) / max(float(np.ptp(field)), 1e-9)
    accent = _palette.mix(_palette.BG, _palette.ACCENTS[rng.integers(6)], 0.35)
    stops = (_palette.DEEP, _palette.BG, accent, _palette.BG, _palette.DEEP)
    small = Image.fromarray(_palette.ramp(t, stops), "RGB")
    return small.resize(size, Image.Resampling.BICUBIC)
