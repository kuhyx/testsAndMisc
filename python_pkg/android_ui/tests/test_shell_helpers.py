"""Tests for shell escaping, focus reads and the adb runner."""

from __future__ import annotations

from pathlib import Path
from typing import NamedTuple

import pytest

from python_pkg.android_ui import driver as drv

MOD = "python_pkg.android_ui.driver"


def _node(text: str = "", **attrs: str) -> str:
    """Render one ``<node>`` element for a fake dump.

    ``attrs`` accepts ``desc``, ``res``, ``cls``, ``bounds``, ``enabled`` and
    ``focused``; each falls back to a representative default.
    """
    return (
        f'<node text="{text}" content-desc="{attrs.get("desc", "")}" '
        f'resource-id="{attrs.get("res", "")}" '
        f'class="{attrs.get("cls", "android.widget.TextView")}" '
        f'bounds="{attrs.get("bounds", "[0,0][100,50]")}" '
        f'enabled="{attrs.get("enabled", "true")}" '
        f'focused="{attrs.get("focused", "false")}"/>'
    )


def _tree(*nodes: str) -> str:
    """Wrap ``nodes`` in a hierarchy document."""
    return f"<?xml version='1.0'?><hierarchy rotation='0'>{''.join(nodes)}</hierarchy>"


class FakeDevice:
    """Scripted stand-in for adb, recording every command it is given."""

    def __init__(self, trees: list[str] | None = None) -> None:
        self.trees = trees or [_tree(_node("Connect"))]
        self.calls: list[tuple[str, ...]] = []
        self.keyboard_shown = False
        self.pulled = 0

    def run(self, *args: str, timeout: float = 30.0) -> str:
        """Answer an adb invocation."""
        del timeout
        self.calls.append(args)
        if args[:2] == ("shell", "dumpsys") and args[2] == "input_method":
            return f"mInputShown={'true' if self.keyboard_shown else 'false'}"
        if args[:2] == ("shell", "dumpsys") and args[2] == "window":
            return "mCurrentFocus=Window{ab12 u0 com.example/com.example.Main}"
        if args[0] == "pull":
            index = min(self.pulled, len(self.trees) - 1)
            self.pulled += 1
            Path(args[2]).write_text(self.trees[index], encoding="utf-8")
        if args[:3] == ("shell", "input", "keyevent") and args[3] in {"111", "4"}:
            self.keyboard_shown = False
        return ""

    def taps(self) -> list[tuple[int, int]]:
        """Return every tap coordinate, in order."""
        return [
            (int(c[3]), int(c[4]))
            for c in self.calls
            if c[:3] == ("shell", "input", "tap")
        ]


class Harness(NamedTuple):
    """A driver plus the fake device backing it.

    Returned as a pair rather than by bolting the device onto the driver, so
    the test needs no attribute that production code does not have.
    """

    ui: drv.AndroidUi
    device: FakeDevice


@pytest.fixture
def ui(monkeypatch: pytest.MonkeyPatch) -> Harness:
    """An :class:`AndroidUi` wired to a :class:`FakeDevice`."""
    device = FakeDevice()
    instance = drv.AndroidUi(settle_seconds=0.0)
    monkeypatch.setattr(instance, "_run", device.run)
    monkeypatch.setattr(f"{MOD}.time.sleep", lambda _s: None)
    return Harness(ui=instance, device=device)


class TestEscape:
    def test_spaces_become_percent_s(self) -> None:
        assert drv._escape("a b") == "a%sb"

    def test_shell_metacharacters_are_escaped(self) -> None:
        assert drv._escape("a&b") == r"a\&b"

    def test_percent_is_escaped_first(self) -> None:
        assert drv._escape("100%") == "100%%"


class TestCurrentFocus:
    def test_returns_the_focused_activity(self, ui: Harness) -> None:
        assert ui.ui.current_focus() == "com.example/com.example.Main"

    def test_empty_when_nothing_matches(
        self, ui: Harness, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(ui.ui, "_run", lambda *a, **k: "no focus here")
        assert ui.ui.current_focus() == ""


class TestRun:
    def test_serial_is_passed_through(self, monkeypatch: pytest.MonkeyPatch) -> None:
        seen: dict[str, list[str]] = {}

        class _Done:
            returncode = 0
            stdout = "ok"
            stderr = ""

        def _fake_run(cmd: list[str], **_kwargs: object) -> _Done:
            seen["cmd"] = cmd
            return _Done()

        monkeypatch.setattr(f"{MOD}.subprocess.run", _fake_run)
        drv.AndroidUi(serial="ABC123")._run("devices")
        assert seen["cmd"][:3] == ["adb", "-s", "ABC123"]

    def test_nonzero_exit_raises_with_stderr(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        class _Done:
            returncode = 1
            stdout = ""
            stderr = "device offline"

        monkeypatch.setattr(f"{MOD}.subprocess.run", lambda *a, **k: _Done())
        with pytest.raises(drv.UiAutomationError, match="device offline"):
            drv.AndroidUi()._run("devices")

    def test_timeout_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def _boom(*_a: object, **_k: object) -> None:
            raise drv.subprocess.TimeoutExpired(cmd="adb", timeout=1)

        monkeypatch.setattr(f"{MOD}.subprocess.run", _boom)
        with pytest.raises(drv.UiAutomationError, match="timed out"):
            drv.AndroidUi()._run("devices")

    def test_unreadable_dump_raises(
        self, ui: Harness, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _no_write(*_a: object, **_k: object) -> str:
            return ""

        monkeypatch.setattr(ui.ui, "_run", _no_write)
        with pytest.raises(drv.UiAutomationError, match="could not read"):
            ui.ui._dump_once()
