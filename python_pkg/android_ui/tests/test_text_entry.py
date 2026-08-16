"""Tests for the keyboard and text-entry half of the driver."""

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


class TestKeyboard:
    def test_reports_whether_the_keyboard_is_up(self, ui: Harness) -> None:
        ui.device.keyboard_shown = True
        assert ui.ui.keyboard_is_up()
        ui.device.keyboard_shown = False
        assert not ui.ui.keyboard_is_up()

    def test_dismiss_is_a_no_op_when_already_closed(self, ui: Harness) -> None:
        ui.ui.dismiss_keyboard()
        assert not [
            c for c in ui.device.calls if c[:3] == ("shell", "input", "keyevent")
        ]

    def test_closes_on_the_second_keyevent_when_escape_is_ignored(
        self, ui: Harness, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Gboard ignores ESCAPE; BACK is the fallback. Exercises the loop
        # running to completion rather than returning on the first check.
        states = iter([True, True, False])
        monkeypatch.setattr(ui.ui, "keyboard_is_up", lambda: next(states, False))
        ui.ui.dismiss_keyboard()
        sent = [
            c[3] for c in ui.device.calls if c[:3] == ("shell", "input", "keyevent")
        ]
        assert sent == ["111", "4"]

    def test_raises_when_the_keyboard_will_not_close(
        self, ui: Harness, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # A keyboard that stays up hides the target; silently continuing would
        # tap a letter key and report success.
        monkeypatch.setattr(ui.ui, "keyboard_is_up", lambda: True)
        with pytest.raises(drv.UiAutomationError, match="still covering"):
            ui.ui.dismiss_keyboard()


class TestTyping:
    def test_verifies_the_field_actually_changed(self, ui: Harness) -> None:
        empty = _node(cls="android.widget.EditText", bounds="[0,0][100,50]")
        filled = _node(
            "typed@example.com",
            cls="android.widget.EditText",
            bounds="[0,0][100,50]",
        )
        ui.device.trees = [_tree(empty), _tree(filled)]
        ui.ui.type_into_field(0, "typed@example.com")

    def test_raises_when_the_tap_did_not_focus_the_field(self, ui: Harness) -> None:
        # The observed failure: keystrokes go nowhere and NOTHING errors.
        empty = _tree(_node(cls="android.widget.EditText", bounds="[0,0][100,50]"))
        ui.device.trees = [empty]
        with pytest.raises(drv.UiAutomationError, match="did not change"):
            ui.ui.type_into_field(0, "typed@example.com")

    def test_clears_a_filled_field_before_typing(self, ui: Harness) -> None:
        # `input text` inserts at the cursor: typing over "old" would produce
        # "oldnew", which passes a naive "did it change?" check and is wrong.
        before = _node("old", cls="android.widget.EditText", bounds="[0,0][100,50]")
        after = _node("new", cls="android.widget.EditText", bounds="[0,0][100,50]")
        ui.device.trees = [_tree(before), _tree(after)]
        ui.ui.type_into_field(0, "new")
        deletes = [
            c
            for c in ui.device.calls
            if c[:3] == ("shell", "input", "keyevent") and c[3] == "67"
        ]
        assert deletes, "expected the field to be cleared first"

    def test_refuses_an_index_the_screen_does_not_have(self, ui: Harness) -> None:
        ui.device.trees = [_tree(_node(cls="android.widget.EditText"))]
        with pytest.raises(drv.ElementNotFoundError, match="has 1"):
            ui.ui.type_into_field(4, "x")

    def test_editable_fields_are_ordered_top_to_bottom(self, ui: Harness) -> None:
        lower = _node(cls="android.widget.EditText", bounds="[0,300][100,350]")
        upper = _node(cls="android.widget.EditText", bounds="[0,100][100,150]")
        ui.device.trees = [_tree(lower, upper)]
        assert [f.bounds[1] for f in ui.ui.editable_fields()] == [100, 300]

    def test_type_into_named_field_verifies_too(self, ui: Harness) -> None:
        before = _node(
            desc="Email", cls="android.widget.EditText", bounds="[0,0][100,50]"
        )
        after = _node(
            "x@y.z", desc="Email", cls="android.widget.EditText", bounds="[0,0][100,50]"
        )
        ui.device.trees = [_tree(before), _tree(before), _tree(after)]
        ui.ui.type_into("Email", "x@y.z")

    def test_type_into_named_field_raises_when_unchanged(self, ui: Harness) -> None:
        node = _node(desc="Email", cls="android.widget.EditText")
        ui.device.trees = [_tree(node)]
        with pytest.raises(drv.UiAutomationError, match="did not change"):
            ui.ui.type_into("Email", "x@y.z")
