"""Tests for linux_configuration/features/monitor_autoconfig.py (I/O shell)."""

from __future__ import annotations

import subprocess
from types import SimpleNamespace
from typing import TYPE_CHECKING

import monitor_autoconfig
from monitor_autoconfig import apply_once, main, watch
import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

OFF = """\
DP-0 connected primary (normal left inverted right x axis y axis)
   3840x2160     60.00 + 144.00
HDMI-0 connected 2560x1440+3840+0 (normal left inverted right x axis y axis)
   2560x1440     59.95 + 143.98*
"""
BEST = """\
DP-0 connected primary 3840x2160+0+0 (normal left inverted right x axis y axis)
   3840x2160     60.00 + 144.00*
HDMI-0 connected 2560x1440+3840+0 (normal left inverted right x axis y axis)
   2560x1440     59.95 + 143.98*
"""
WANT = [
    "xrandr", "--output", "DP-0", "--mode", "3840x2160", "--rate", "144.00",
    "--pos", "0x0", "--primary", "--output", "HDMI-0", "--mode", "2560x1440",
    "--rate", "143.98", "--pos", "3840x0",
]  # fmt: skip


NO_MODES_YET = """\
DP-0 connected primary (normal left inverted right x axis y axis)
HDMI-0 connected 2560x1440+3840+0 (normal left inverted right x axis y axis)
   2560x1440     59.95 + 143.98*
"""


class FakeXrandr:
    """Serves queued ``xrandr --query`` texts and records apply calls."""

    def __init__(self, *queries: str, fail_apply: bool = False) -> None:
        self.queries = list(queries)
        self.applied: list[list[str]] = []
        self.fail_apply = fail_apply

    def __call__(self, argv: list[str]) -> str:
        if argv == ["xrandr", "--query"]:
            return self.queries.pop(0)
        self.applied.append(argv)
        if self.fail_apply:
            raise subprocess.CalledProcessError(1, argv, stderr="crtc failed")
        return ""


class FakeDisplay:
    """Xlib display double: ``events`` batches, then the X server goes away."""

    def __init__(self, batches: list[int]) -> None:
        self.batches = batches
        self.pending = 0
        self.selected: list[int] = []
        self.handshakes = 0
        root = type("Root", (), {"xrandr_select_input": self.selected.append})()
        self.screen: Callable[[], object] = type("S", (), {"root": root})

    def next_event(self) -> None:
        if self.pending:
            self.pending -= 1
            return
        if not self.batches:
            raise ConnectionError
        self.pending = self.batches.pop(0) - 1

    def pending_events(self) -> int:
        return self.pending

    def xrandr_query_version(self) -> None:
        """X only sends RandR 1.2+ output events after this handshake."""
        self.handshakes += 1


def test_apply_once_runs_planned_xrandr() -> None:
    """An off monitor gets switched on with one xrandr call."""
    fake = FakeXrandr(OFF)
    assert apply_once("DP-0", run=fake) is True
    assert fake.applied == [WANT]


def test_apply_once_noop_when_best() -> None:
    """Already-best layout means no xrandr call (no flicker on stray events)."""
    fake = FakeXrandr(BEST)
    assert apply_once("DP-0", run=fake) is False
    assert fake.applied == []


def test_watch_applies_at_start_and_once_per_burst() -> None:
    """A burst of 3 hotplug events is drained and handled by one apply."""
    fake = FakeXrandr(OFF, BEST)
    display = FakeDisplay([3])
    with pytest.raises(ConnectionError):
        watch("DP-0", display=display, run=fake, settle=lambda: None)
    assert display.handshakes == 1
    assert display.selected == [monitor_autoconfig.OUTPUT_CHANGE_MASK]
    assert fake.applied == [WANT]
    assert fake.queries == []


def test_main_dry_run_prints_command(capsys: pytest.CaptureFixture[str]) -> None:
    """``--dry-run`` prints the xrandr command and changes nothing."""
    fake = FakeXrandr(OFF)
    assert main(["--dry-run"], run=fake) == 0
    assert capsys.readouterr().out.split() == WANT
    assert fake.applied == []


def test_main_once_applies(monkeypatch: pytest.MonkeyPatch) -> None:
    """``--once`` applies the layout and exits without watching."""
    fake = FakeXrandr(OFF)
    monkeypatch.setattr(monitor_autoconfig, "watch", pytest.fail)
    assert main(["--once", "--primary", "DP-0"], run=fake) == 0
    assert fake.applied == [WANT]


def test_main_default_watches(monkeypatch: pytest.MonkeyPatch) -> None:
    """With no mode flag, ``main`` hands off to ``watch``."""
    seen: list[str] = []
    monkeypatch.setattr(monitor_autoconfig, "watch", seen.append)
    assert main([]) == 0
    assert seen == ["DP-0"]


def test_apply_once_waits_for_late_edid_modes() -> None:
    """A just-plugged monitor with no modes yet is re-queried, then applied."""
    fake = FakeXrandr(NO_MODES_YET, OFF)
    settles: list[None] = []
    assert apply_once("DP-0", run=fake, settle=lambda: settles.append(None))
    assert settles == [None]
    assert fake.applied == [WANT]


def test_apply_once_gives_up_waiting_after_tries() -> None:
    """Modes that never appear stop the retry; the rest is still laid out."""
    fake = FakeXrandr(NO_MODES_YET, NO_MODES_YET)
    assert apply_once("DP-0", run=fake, settle=lambda: None, tries=2) is True
    assert fake.applied[0][:3] == ["xrandr", "--output", "HDMI-0"]


def test_watch_survives_failed_xrandr(capsys: pytest.CaptureFixture[str]) -> None:
    """A failing apply is logged and the watcher keeps handling events."""
    fake = FakeXrandr(OFF, OFF, fail_apply=True)
    with pytest.raises(ConnectionError):
        watch("DP-0", display=FakeDisplay([1]), run=fake, settle=lambda: None)
    assert fake.applied == [WANT, WANT]
    assert "crtc failed" in capsys.readouterr().err


def test_run_returns_stdout(monkeypatch: pytest.MonkeyPatch) -> None:
    """``_run`` is a checked subprocess call returning stdout."""
    calls: list[tuple[list[str], dict[str, object]]] = []

    def fake_run(argv: list[str], **kwargs: object) -> SimpleNamespace:
        calls.append((argv, kwargs))
        return SimpleNamespace(stdout="out")

    monkeypatch.setattr(monitor_autoconfig.subprocess, "run", fake_run)
    assert monitor_autoconfig._run(["xrandr"]) == "out"
    assert calls[0][1]["check"] is True


def test_open_display_uses_xlib(monkeypatch: pytest.MonkeyPatch) -> None:
    """The real display comes from ``Xlib.display.Display()``."""
    sentinel = object()
    fake_module = SimpleNamespace(Display=lambda: sentinel)
    monkeypatch.setattr(
        monitor_autoconfig.importlib, "import_module", lambda name: fake_module
    )
    assert monitor_autoconfig._open_display() is sentinel


def test_settle_sleeps_settle_seconds(monkeypatch: pytest.MonkeyPatch) -> None:
    """The real settle waits ``SETTLE_SECONDS`` for EDID to arrive."""
    slept: list[float] = []
    monkeypatch.setattr(monitor_autoconfig.time, "sleep", slept.append)
    monitor_autoconfig._settle()
    assert slept == [monitor_autoconfig.SETTLE_SECONDS]
