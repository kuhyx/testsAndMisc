"""Style 3: a year of habits as four stacked day grids, colour only."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta
import json
from typing import TYPE_CHECKING, cast

from PIL import Image, ImageDraw

from python_pkg.wallpaper_rotator import _palette

if TYPE_CHECKING:
    from pathlib import Path

    import numpy as np

    from python_pkg.wallpaper_rotator._context import RenderContext

# Ledger directory under ~/.local/share -> the colour of its grid.
HABITS: tuple[tuple[str, _palette.Rgb], ...] = (
    ("workout_locker", _palette.GREEN),
    ("leetcode_guard", _palette.ORANGE),
    ("anki_guard", _palette.CYAN),
    ("book_guard", _palette.PURPLE),
)
WEEKS = 52
_EMPTY = _palette.mix(_palette.BG, _palette.LINE, 0.5)
_FULL_AT = 3  # credits in a day that light a cell fully


def credit_days(ledger: Path) -> Counter[date]:
    """Count the non-zero ``credit`` rows per day in one guard ledger.

    A missing or unreadable ledger yields no days: the grid stays empty
    rather than the background failing.
    """
    try:
        data = json.loads(ledger.read_text(encoding="utf-8"))
    except OSError, ValueError:
        return Counter()
    rows = data.get("entries", []) if isinstance(data, dict) else []
    days: Counter[date] = Counter()
    for row in cast("list[object]", rows):
        if not isinstance(row, dict) or row.get("kind") != "credit":
            continue
        if row.get("amount", 1) == 0:
            continue
        try:
            days[date.fromisoformat(str(row.get("day")))] += 1
        except ValueError:
            continue
    return days


@dataclass(frozen=True)
class _Grid:
    """Where the day cells sit: first day, left edge, cell pitch and size."""

    today: date
    start: date
    left: float
    pitch: float
    cell: float


def _cell_colour(count: int, colour: _palette.Rgb) -> _palette.Rgb:
    if count <= 0:
        return _EMPTY
    return _palette.mix(_EMPTY, colour, 0.35 + 0.45 * min(count, _FULL_AT) / _FULL_AT)


def _draw_band(
    draw: ImageDraw.ImageDraw,
    grid: _Grid,
    band_top: float,
    days: Counter[date],
    colour: _palette.Rgb,
) -> None:
    """Fill one habit's 7-row grid, oldest day at the left."""
    for offset in range((grid.today - grid.start).days + 1):
        day = grid.start + timedelta(days=offset)
        x = grid.left + (offset // 7) * grid.pitch
        y = band_top + day.weekday() * grid.pitch
        draw.rectangle(
            (x, y, x + grid.cell, y + grid.cell),
            fill=_cell_colour(days[day], colour),
        )


def render(
    ctx: RenderContext, size: tuple[int, int], _rng: np.random.Generator
) -> Image.Image:
    """Draw one 7-row x 53-column grid per habit, today at the bottom right."""
    width, height = size
    image = Image.new("RGB", size, _palette.DEEP)
    draw = ImageDraw.Draw(image)
    today = ctx.now.date()
    columns = WEEKS + 1
    band_gap = 2  # cells of space between habits
    rows = 7 * len(HABITS) + band_gap * (len(HABITS) - 1)
    pitch = min(width * 0.86 / columns, height * 0.8 / rows)
    grid = _Grid(
        today=today,
        start=today - timedelta(days=today.weekday() + 7 * WEEKS),
        left=(width - pitch * columns) / 2,
        pitch=pitch,
        cell=max(pitch * 0.82, 1.0),
    )
    top = (height - pitch * rows) / 2
    for band, (folder, colour) in enumerate(HABITS):
        days = credit_days(ctx.data_home / folder / "ledger.json")
        band_top = top + band * (7 + band_gap) * pitch
        _draw_band(draw, grid, band_top, days, colour)
    return image
