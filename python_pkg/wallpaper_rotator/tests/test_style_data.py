"""Branches of the data-driven styles: clock conf, habit ledgers, Earth maps."""

from __future__ import annotations

from datetime import UTC, date, datetime
import json
from typing import TYPE_CHECKING

import numpy as np
from PIL import Image

from python_pkg.wallpaper_rotator import _style_clock as _clock
from python_pkg.wallpaper_rotator import _style_earth as _earth
from python_pkg.wallpaper_rotator import _style_heatmap as _heatmap
from python_pkg.wallpaper_rotator._context import RenderContext

if TYPE_CHECKING:
    from pathlib import Path


def _ctx(tmp_path: Path, now: datetime, conf: Path | None = None) -> RenderContext:
    return RenderContext(
        now=now,
        data_home=tmp_path / "share",
        earth_dir=tmp_path / "earth",
        shutdown_conf=conf or tmp_path / "missing.conf",
    )


def test_schedule_defaults_when_conf_is_missing(tmp_path: Path) -> None:
    assert _clock.schedule(tmp_path / "nope.conf", 0) == (300, 1380)


def test_schedule_reads_numbers_and_skips_junk_lines(tmp_path: Path) -> None:
    conf = tmp_path / "s.conf"
    conf.write_text(
        "no equals sign\n"
        "MON_WED_MINUTES=1200\n"
        "THU_SUN_MINUTES = 1300 \n"
        "MORNING_END_MINUTES=abc\n",
        encoding="utf-8",
    )
    assert _clock.schedule(conf, 2) == (300, 1200)
    assert _clock.schedule(conf, 3) == (300, 1300)


def test_clock_after_shutdown_draws_only_the_dim_ring(tmp_path: Path) -> None:
    late = _ctx(tmp_path, datetime(2026, 11, 11, 23, 30, tzinfo=UTC))
    image = _clock.render(late, (200, 120), np.random.default_rng(0))
    assert image.size == (200, 120)


def test_clock_tone_is_calmer_hours_before_shutdown(tmp_path: Path) -> None:
    early = _ctx(tmp_path, datetime(2026, 11, 11, 8, 0, tzinfo=UTC))
    late = _ctx(tmp_path, datetime(2026, 11, 11, 22, 30, tzinfo=UTC))
    rng = np.random.default_rng(0)
    corner_early = _clock.render(early, (200, 120), rng).getpixel((100, 5))
    corner_late = _clock.render(late, (200, 120), rng).getpixel((100, 5))
    assert corner_early != corner_late


def _ledger(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "ledger.json"
    path.write_text(text, encoding="utf-8")
    return path


def test_credit_days_counts_real_credits_per_day(tmp_path: Path) -> None:
    entries = [
        {"kind": "credit", "amount": 5, "day": "2026-11-10"},
        {"kind": "credit", "day": "2026-11-10"},
        {"kind": "credit", "amount": 1, "day": "2026-11-09"},
    ]
    days = _heatmap.credit_days(_ledger(tmp_path, json.dumps({"entries": entries})))
    assert days == {date(2026, 11, 10): 2, date(2026, 11, 9): 1}


def test_credit_days_ignores_unusable_rows(tmp_path: Path) -> None:
    entries = [
        "not a dict",
        {"kind": "debit", "amount": 3, "day": "2026-11-10"},
        {"kind": "credit", "amount": 0, "day": "2026-11-10"},
        {"kind": "credit", "amount": 1, "day": "yesterday"},
        {"kind": "credit", "amount": 1},
    ]
    days = _heatmap.credit_days(_ledger(tmp_path, json.dumps({"entries": entries})))
    assert not days


def test_credit_days_survives_a_broken_ledger(tmp_path: Path) -> None:
    assert not _heatmap.credit_days(tmp_path / "missing.json")
    assert not _heatmap.credit_days(_ledger(tmp_path, "{not json"))
    assert not _heatmap.credit_days(_ledger(tmp_path, "[1, 2]"))
    assert not _heatmap.credit_days(_ledger(tmp_path, "{}"))


def test_heatmap_lights_cells_for_credit_days(tmp_path: Path) -> None:
    now = datetime(2026, 11, 11, 12, 0, tzinfo=UTC)
    ctx = _ctx(tmp_path, now)
    folder = ctx.data_home / "workout_locker"
    folder.mkdir(parents=True)
    rows = [{"kind": "credit", "amount": 1, "day": "2026-11-11"}] * 3
    (folder / "ledger.json").write_text(json.dumps({"entries": rows}), encoding="utf-8")
    lit = _heatmap.render(ctx, (800, 480), np.random.default_rng(0))
    blank = _heatmap.render(
        _ctx(tmp_path / "x", now), (800, 480), np.random.default_rng(0)
    )
    assert lit.tobytes() != blank.tobytes()


def test_earth_available_needs_both_images(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path, datetime(2026, 11, 11, tzinfo=UTC))
    assert not _earth.available(ctx)
    ctx.earth_dir.mkdir()
    Image.new("RGB", (4, 2)).save(ctx.earth_dir / "day.jpg")
    assert not _earth.available(ctx)
    Image.new("RGB", (4, 2)).save(ctx.earth_dir / "night.jpg")
    assert _earth.available(ctx)


def test_sun_is_over_the_greenwich_meridian_at_noon_utc(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path, datetime(2026, 3, 20, 12, 0, tzinfo=UTC))
    lat, lon = _earth.sun_position(ctx)
    assert lon == 0.0
    assert abs(lat) < np.radians(24)
