"""Style 4: the time left until tonight's shutdown, as colour and an arc."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from PIL import Image, ImageDraw

from python_pkg.wallpaper_rotator import _palette

if TYPE_CHECKING:
    from pathlib import Path

    from python_pkg.wallpaper_rotator._context import RenderContext

_DEFAULT_SHUTDOWN = 23 * 60
_DEFAULT_MORNING = 5 * 60
_LAST_MON_WED = 2  # Monday..Wednesday use the early shutdown
_WARN_MINUTES = 120  # colour moves blue -> red over the last two hours
_CALM = _palette.mix(_palette.DEEP, _palette.COMMENT, 0.45)
_HALF = 0.5
_ALARM = (0x5A, 0x16, 0x22)


def _read_conf(conf: Path) -> dict[str, int]:
    values: dict[str, int] = {}
    try:
        text = conf.read_text(encoding="utf-8")
    except OSError:
        return values
    for line in text.splitlines():
        key, sep, value = line.partition("=")
        if sep and value.strip().isdigit():
            values[key.strip()] = int(value.strip())
    return values


def schedule(conf: Path, weekday: int) -> tuple[int, int]:
    """Return (morning end, shutdown) in minutes after midnight for a weekday."""
    values = _read_conf(conf)
    key = "MON_WED_MINUTES" if weekday <= _LAST_MON_WED else "THU_SUN_MINUTES"
    return (
        values.get("MORNING_END_MINUTES", _DEFAULT_MORNING),
        values.get(key, _DEFAULT_SHUTDOWN),
    )


def _glow(tone: _palette.Rgb, size: tuple[int, int]) -> Image.Image:
    """A radial wash from ``tone`` at the centre to DEEP at the corners."""
    width, height = size
    small_w, small_h = max(width // 4, 2), max(height // 4, 2)
    ys, xs = np.indices((small_h, small_w), dtype=np.float64)
    radial = np.hypot(xs / small_w - 0.5, ys / small_h - 0.5) / 0.71
    glow = Image.fromarray(_palette.ramp(radial, (tone, _palette.DEEP)), "RGB")
    return glow.resize(size, Image.Resampling.BICUBIC)


def _draw_arcs(
    image: Image.Image, tone: _palette.Rgb, urgency: float, share: float
) -> None:
    """Draw the dim full ring and, over it, the arc of day still left."""
    width, height = image.size
    radius = min(width, height) * 0.32
    box = (
        width / 2 - radius,
        height / 2 - radius,
        width / 2 + radius,
        height / 2 + radius,
    )
    line = max(round(min(width, height) / 180), 1)
    draw = ImageDraw.Draw(image)
    draw.arc(
        box, 0, 360, fill=_palette.mix(_palette.DEEP, _palette.LINE, 0.9), width=line
    )
    if share > 0:
        bright = _palette.mix(
            tone, _palette.CYAN if urgency < _HALF else _palette.RED, 0.5
        )
        draw.arc(box, -90, -90 + 360 * share, fill=bright, width=line)


def render(
    ctx: RenderContext, size: tuple[int, int], _rng: np.random.Generator
) -> Image.Image:
    """Tint the screen by urgency; a thin arc shows the share of day left."""
    morning, shutdown = schedule(ctx.shutdown_conf, ctx.now.weekday())
    minute = ctx.now.hour * 60 + ctx.now.minute
    left = max(shutdown - minute, 0)
    urgency = 1.0 - min(left, _WARN_MINUTES) / _WARN_MINUTES
    tone = _palette.mix(_CALM, _ALARM, urgency)
    image = _glow(tone, size)
    share = min(left / max(shutdown - morning, 1), 1.0)
    _draw_arcs(image, tone, urgency, share)
    return image
