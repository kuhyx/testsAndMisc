"""Style 2: fresh procedural art each showing (flow field or Voronoi)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from PIL import Image, ImageDraw

from python_pkg.wallpaper_rotator import _palette

if TYPE_CHECKING:
    from python_pkg.wallpaper_rotator._context import RenderContext

_STEPS = 90
_SITES = 36
_TINTED_SHARE = 0.2  # fraction of Voronoi cells given an accent tint
_FLOW_SHARE = 0.5  # chance of the flow field over Voronoi


def _angle_field(xs: np.ndarray, ys: np.ndarray, waves: np.ndarray) -> np.ndarray:
    """Cheap smooth noise: a sum of sines in each particle's position."""
    total = np.zeros_like(xs)
    for fx, fy, phase in waves:
        total += np.sin(xs * fx + ys * fy + phase)
    return total * np.pi


def _trace(
    start: tuple[np.ndarray, np.ndarray],
    size: tuple[int, int],
    waves: np.ndarray,
) -> np.ndarray:
    """Step every particle along the angle field; return all positions."""
    xs, ys = start
    width, height = size
    step = max(width, height) / 600
    trails = np.empty((_STEPS, len(xs), 2))
    for i in range(_STEPS):
        trails[i, :, 0], trails[i, :, 1] = xs, ys
        angle = _angle_field(xs / width * 4, ys / height * 4, waves)
        xs = xs + np.cos(angle) * step
        ys = ys + np.sin(angle) * step
    return trails


def _flow(size: tuple[int, int], rng: np.random.Generator) -> Image.Image:
    """Trace particles through a smooth angle field as translucent strokes."""
    width, height = size
    image = Image.new("RGB", size, _palette.DEEP)
    draw = ImageDraw.Draw(image, "RGBA")
    count = max(width * height // 2000, 50)
    xs = rng.uniform(0, width, count)
    ys = rng.uniform(0, height, count)
    waves = rng.uniform([0.5, 0.5, 0.0], [3.0, 3.0, 6.3], size=(3, 3))
    trails = _trace((xs, ys), size, waves)
    colours = [_palette.ACCENTS[k] for k in rng.choice(6, size=2, replace=False)]
    line_width = max(width // 1500, 1)
    for p in range(count):
        r, g, b = colours[p % 2]
        points = [(float(x), float(y)) for x, y in trails[:, p]]
        draw.line(points, fill=(r, g, b, 40), width=line_width)
    return image


def _nearest_sites(
    grid: tuple[np.ndarray, np.ndarray], sites: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Per pixel: distance to the nearest and second-nearest site, and owner."""
    xs, ys = grid
    best = np.full(xs.shape, np.inf)
    second = np.full(xs.shape, np.inf)
    owner = np.zeros(xs.shape, dtype=np.int64)
    for k, (sx, sy) in enumerate(sites):
        dist = np.hypot(xs - sx, ys - sy)
        closer = dist < best
        second = np.where(closer, best, np.minimum(second, dist))
        owner = np.where(closer, k, owner)
        best = np.where(closer, dist, best)
    return best, second, owner


def _voronoi(size: tuple[int, int], rng: np.random.Generator) -> Image.Image:
    """Shade Voronoi cells darker towards their edges, a few cells tinted."""
    width, height = size
    half_w, half_h = max(width // 2, 1), max(height // 2, 1)
    ys, xs = np.indices((half_h, half_w), dtype=np.float64)
    sites = rng.uniform([0, 0], [half_w, half_h], size=(_SITES, 2))
    best, second, owner = _nearest_sites((xs, ys), sites)
    edge = np.clip((second - best) / (0.05 * max(half_w, half_h)), 0.0, 1.0)
    tints = [_palette.mix(_palette.BG, c, 0.25) for c in _palette.ACCENTS]
    cell_colour = np.array(
        [
            tints[rng.integers(6)] if rng.random() < _TINTED_SHARE else _palette.BG
            for _ in sites
        ],
        dtype=np.float64,
    )
    deep = np.array(_palette.DEEP, dtype=np.float64)
    rgb = deep + (cell_colour[owner] - deep) * edge[..., None]
    small = Image.fromarray(rgb.round().astype(np.uint8), "RGB")
    return small.resize(size, Image.Resampling.BILINEAR)


def render(
    _ctx: RenderContext, size: tuple[int, int], rng: np.random.Generator
) -> Image.Image:
    """Pick one of the two generators and run it with a fresh seed."""
    return _flow(size, rng) if rng.random() < _FLOW_SHARE else _voronoi(size, rng)
