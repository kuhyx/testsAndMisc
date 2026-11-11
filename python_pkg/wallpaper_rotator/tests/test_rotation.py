"""Tests for the 3-hourly style rotation and its state."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import random
from typing import TYPE_CHECKING

from python_pkg.wallpaper_rotator._rotation import Pick, State, choose, plan

if TYPE_CHECKING:
    from pathlib import Path

_NAMES = ["clock", "earth", "gradient", "heatmap", "plasma", "procedural"]
_T0 = datetime(2026, 11, 11, 12, 0, tzinfo=UTC)
_OUTS = ["DP-0", "HDMI-0"]


def test_choose_differs_from_previous_and_between_outputs() -> None:
    rng = random.SystemRandom()
    previous = {"DP-0": "plasma", "HDMI-0": "earth"}
    for _ in range(200):
        picked = choose(previous, _OUTS, _NAMES, rng)
        assert picked["DP-0"] != previous["DP-0"]
        assert picked["HDMI-0"] != previous["HDMI-0"]
        assert picked["DP-0"] != picked["HDMI-0"]
        previous = picked


def test_first_run_rotates_and_paints() -> None:
    state, paint = plan(None, _OUTS, _T0, _NAMES, random.SystemRandom(), root_id="0x1")
    assert paint
    assert set(state.picks) == set(_OUTS)
    assert state.rotated_at == _T0


def test_static_styles_untouched_before_three_hours() -> None:
    old = State(_T0, {o: Pick("plasma", 5) for o in _OUTS}, root_id="0x1")
    state, paint = plan(
        old,
        _OUTS,
        _T0 + timedelta(hours=2),
        _NAMES,
        random.SystemRandom(),
        root_id="0x1",
    )
    assert not paint
    assert state == old


def test_data_styles_redraw_with_same_style_before_three_hours() -> None:
    old = State(
        _T0, {"DP-0": Pick("clock", 5), "HDMI-0": Pick("plasma", 6)}, root_id="0x1"
    )
    state, paint = plan(
        old,
        _OUTS,
        _T0 + timedelta(minutes=15),
        _NAMES,
        random.SystemRandom(),
        root_id="0x1",
    )
    assert paint
    assert state.picks == old.picks


def test_lost_root_pixmap_repaints_same_styles() -> None:
    old = State(_T0, {o: Pick("plasma", 5) for o in _OUTS}, root_id="0x1")
    state, paint = plan(
        old,
        _OUTS,
        _T0 + timedelta(hours=1),
        _NAMES,
        random.SystemRandom(),
        root_id=None,
    )
    assert paint
    assert state.picks == old.picks


def test_three_hours_rotates_to_new_styles() -> None:
    old = State(
        _T0, {"DP-0": Pick("plasma", 5), "HDMI-0": Pick("earth", 6)}, root_id="0x1"
    )
    later = _T0 + timedelta(hours=3)
    state, paint = plan(old, _OUTS, later, _NAMES, random.SystemRandom(), root_id="0x1")
    assert paint
    assert state.rotated_at == later
    assert state.picks["DP-0"].style != "plasma"
    assert state.picks["HDMI-0"].style != "earth"


def test_state_round_trips_through_json(tmp_path: Path) -> None:
    old = State(_T0, {"DP-0": Pick("clock", 5)}, root_id="0x1")
    path = tmp_path / "state.json"
    old.save(path)
    assert State.load(path) == old
    assert State.load(tmp_path / "missing.json") is None


def test_state_load_rejects_unreadable_content(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    bad_date = '{"rotated_at": "x", "picks": {}, "root_id": null}'
    for text in ("not json", "{}", '{"picks": {"a": [1]}}', bad_date):
        path.write_text(text, encoding="utf-8")
        assert State.load(path) is None


def test_new_output_gets_a_style_unlike_the_others() -> None:
    old = State(_T0, {"DP-0": Pick("plasma", 5)}, root_id="0x1")
    state, paint = plan(
        old,
        _OUTS,
        _T0 + timedelta(hours=1),
        _NAMES,
        random.SystemRandom(),
        root_id="0x1",
    )
    assert paint
    assert state.picks["DP-0"] == old.picks["DP-0"]
    assert state.picks["HDMI-0"].style != "plasma"


def test_new_output_falls_back_to_all_names_when_none_unused() -> None:
    old = State(_T0, {"DP-0": Pick("plasma", 5)}, root_id="0x1")
    state, paint = plan(
        old,
        _OUTS,
        _T0 + timedelta(hours=1),
        ["plasma"],
        random.SystemRandom(),
        root_id="0x1",
    )
    assert paint
    assert state.picks["HDMI-0"].style == "plasma"


def test_rotation_with_stale_state_missing_an_output() -> None:
    old = State(_T0, {"DP-0": Pick("plasma", 5)}, root_id="0x1")
    state, paint = plan(
        old,
        _OUTS,
        _T0 + timedelta(hours=4),
        _NAMES,
        random.SystemRandom(),
        root_id="0x1",
    )
    assert paint
    assert set(state.picks) == set(_OUTS)
    assert state.picks["DP-0"].style != "plasma"


def test_choose_reuses_names_when_every_option_is_taken() -> None:
    picked = choose({"DP-0": "plasma"}, ["DP-0"], ["plasma"], random.SystemRandom())
    assert picked == {"DP-0": "plasma"}
