"""Tests for one timer tick, with i3-msg, xprop and feh replaced by fakes."""

from __future__ import annotations

from datetime import UTC, datetime
import json
import random
import subprocess
from typing import TYPE_CHECKING

import pytest

from python_pkg.wallpaper_rotator import _tick
from python_pkg.wallpaper_rotator._context import RenderContext
from python_pkg.wallpaper_rotator._rotation import Pick, State

if TYPE_CHECKING:
    from pathlib import Path

    from PIL import Image

_NOW = datetime(2026, 11, 11, 12, 0, tzinfo=UTC)
_OUTPUTS = [
    {
        "name": "DP-0",
        "active": True,
        "rect": {"x": 0, "y": 0, "width": 64, "height": 36},
    },
    {
        "name": "off",
        "active": False,
        "rect": {"x": 0, "y": 0, "width": 1, "height": 1},
    },
]


def _completed(stdout: str) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=[], returncode=0, stdout=stdout)


@pytest.fixture
def ctx(tmp_path: Path) -> RenderContext:
    return RenderContext(
        now=_NOW,
        data_home=tmp_path / "share",
        earth_dir=tmp_path / "no-earth",
        shutdown_conf=tmp_path / "missing.conf",
    )


@pytest.fixture
def world(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, ctx: RenderContext
) -> list[Image.Image]:
    """Fake every outside effect; return the list of root images "painted"."""
    painted: list[Image.Image] = []
    monkeypatch.setattr(_tick, "STATE_FILE", tmp_path / "state.json")
    monkeypatch.setattr(_tick, "ROOT_IMAGE", tmp_path / "root.png")
    monkeypatch.setattr(_tick, "i3_outputs", lambda: _OUTPUTS)
    monkeypatch.setattr(_tick, "root_identity", lambda display=None: "7:0x1")
    monkeypatch.setattr(RenderContext, "live", classmethod(lambda _cls: ctx))
    monkeypatch.setattr(
        _tick._paint, "apply", lambda root, _target: painted.append(root)
    )
    return painted


def test_i3_outputs_parses_i3_msg_json(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], **_kw: object) -> subprocess.CompletedProcess[str]:
        calls.append(cmd)
        return _completed(json.dumps(_OUTPUTS))

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert _tick.i3_outputs() == _OUTPUTS
    assert calls == [["/usr/bin/i3-msg", "-t", "get_outputs"]]


def test_root_identity_joins_server_pid_and_pixmap(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / ".X1-lock").write_text("  4242\n", encoding="utf-8")
    monkeypatch.setattr(_tick, "_X_LOCK_DIR", tmp_path)
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *_a, **_kw: _completed("_XROOTPMAP_ID(PIXMAP) # 0x4a00003\n"),
    )
    assert _tick.root_identity(":1.0") == "4242:0x4a00003"


def test_root_identity_reads_display_from_environment(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / ".X5-lock").write_text("9\n", encoding="utf-8")
    monkeypatch.setattr(_tick, "_X_LOCK_DIR", tmp_path)
    monkeypatch.setenv("DISPLAY", ":5")
    monkeypatch.setattr(subprocess, "run", lambda *_a, **_kw: _completed("# 0xab"))
    assert _tick.root_identity() == "9:0xab"


def test_root_identity_without_lock_file_or_pixmap(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(_tick, "_X_LOCK_DIR", tmp_path)
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *_a, **_kw: _completed("_XROOTPMAP_ID:  not found.\n"),
    )
    assert _tick.root_identity(":0") is None


def test_root_identity_marks_unreadable_lock_with_question_mark(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(_tick, "_X_LOCK_DIR", tmp_path)
    monkeypatch.setattr(subprocess, "run", lambda *_a, **_kw: _completed("# 0x1"))
    assert _tick.root_identity(":0") == "?:0x1"


def test_first_tick_paints_and_saves_state(world: list[Image.Image]) -> None:
    assert _tick.tick(random.SystemRandom()) is True
    assert len(world) == 1
    assert world[0].size == (64, 36)
    state = State.load(_tick.STATE_FILE)
    assert state is not None
    assert set(state.picks) == {"DP-0"}
    assert state.root_id == "7:0x1"


def test_tick_defaults_to_a_fresh_rng(world: list[Image.Image]) -> None:
    assert _tick.tick() is True
    assert len(world) == 1


def test_idle_tick_leaves_the_background_alone(world: list[Image.Image]) -> None:
    State(_NOW, {"DP-0": Pick("plasma", 1)}, root_id="7:0x1").save(_tick.STATE_FILE)
    assert _tick.tick(random.SystemRandom()) is False
    assert not world


def test_live_style_redraws_and_skips_unplugged_outputs(
    world: list[Image.Image],
) -> None:
    State(
        _NOW,
        {"DP-0": Pick("clock", 1), "gone": Pick("clock", 2)},
        root_id="7:0x1",
    ).save(_tick.STATE_FILE)
    assert _tick.tick(random.SystemRandom()) is True
    assert len(world) == 1
    state = State.load(_tick.STATE_FILE)
    assert state is not None
    assert state.picks["DP-0"].style == "clock"
