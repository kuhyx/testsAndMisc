"""Style 5: the Earth now, lit side from Blue Marble, dark side from Black Marble.

Images: NASA Earth Observatory, public domain; fetched by install.sh.
"""

from __future__ import annotations

from datetime import UTC
from typing import TYPE_CHECKING

import numpy as np
from PIL import Image

from python_pkg.wallpaper_rotator import _palette

if TYPE_CHECKING:
    from python_pkg.wallpaper_rotator._context import RenderContext

_DAY = "day.jpg"
_NIGHT = "night.jpg"
_TWILIGHT = 0.12  # width of the soft terminator, in cos(zenith)
_DAY_DIM = 0.45  # keep the lit side well below "blinding"


def available(ctx: RenderContext) -> bool:
    """Both source images are on disk."""
    return (ctx.earth_dir / _DAY).is_file() and (ctx.earth_dir / _NIGHT).is_file()


def sun_position(ctx: RenderContext) -> tuple[float, float]:
    """Approximate subsolar (latitude, longitude) in radians for ``ctx.now``."""
    utc = ctx.now.astimezone(UTC)
    day_of_year = utc.timetuple().tm_yday
    declination = np.radians(-23.44) * np.cos(2 * np.pi * (day_of_year + 10) / 365)
    hours = utc.hour + utc.minute / 60
    return float(declination), float(np.radians((12.0 - hours) * 15.0))


def _load(ctx: RenderContext, name: str, size: tuple[int, int]) -> np.ndarray:
    with Image.open(ctx.earth_dir / name) as raw:
        rgb = raw.convert("RGB").resize(size, Image.Resampling.LANCZOS)
    return np.asarray(rgb, dtype=np.float64)


def render(
    ctx: RenderContext, size: tuple[int, int], _rng: np.random.Generator
) -> Image.Image:
    """Blend day and night maps along the real terminator, letterboxed."""
    width, height = size
    map_w = width
    map_h = min(width // 2, height)
    lat = np.linspace(np.pi / 2, -np.pi / 2, map_h)[:, None]
    lon = np.linspace(-np.pi, np.pi, map_w)[None, :]
    sun_lat, sun_lon = sun_position(ctx)
    cos_zenith = np.sin(lat) * np.sin(sun_lat) + np.cos(lat) * np.cos(sun_lat) * np.cos(
        lon - sun_lon
    )
    lit = np.clip(cos_zenith / _TWILIGHT + 0.5, 0.0, 1.0)[..., None]
    day = _load(ctx, _DAY, (map_w, map_h)) * _DAY_DIM
    night = _load(ctx, _NIGHT, (map_w, map_h))
    earth = (day * lit + night * (1.0 - lit)).round().astype(np.uint8)
    image = Image.new("RGB", size, _palette.DEEP)
    image.paste(Image.fromarray(earth, "RGB"), (0, (height - map_h) // 2))
    return image
