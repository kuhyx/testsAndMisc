"""Tests for :mod:`python_pkg.android_ui.driver`.

The cases mirror failures actually observed driving a Pixel 6a on 2026-08-10,
because each of them looked like success at the time:

* a tap that landed on an unfocused field, so the typed text went nowhere;
* a widget behind the soft keyboard whose reported position was 390px off;
* ``uiautomator dump`` returning only the focused ``EditText`` nodes;
* ``input text`` appending to a filled field instead of replacing it.
"""

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


class TestParseTree:
    def test_keeps_labelled_nodes(self) -> None:
        elements = drv._parse_tree(_tree(_node("Connect Firebase")))
        assert [e.text for e in elements] == ["Connect Firebase"]

    def test_keeps_empty_edit_text(self) -> None:
        # An empty field has no text, content-desc or resource-id, yet it is
        # exactly the element a caller must address in order to fill it in.
        xml = _tree(_node(cls="android.widget.EditText"))
        assert len(drv._parse_tree(xml)) == 1

    def test_drops_unlabelled_non_editable_nodes(self) -> None:
        assert drv._parse_tree(_tree(_node())) == []

    def test_drops_nodes_without_bounds(self) -> None:
        xml = _tree('<node text="x" class="android.widget.TextView"/>')
        assert drv._parse_tree(xml) == []

    def test_malformed_xml_is_an_empty_screen_not_a_crash(self) -> None:
        # A dump taken mid-animation is truncated; callers retry rather than die.
        assert drv._parse_tree("<hierarchy><node") == []


class TestUiElement:
    def test_center_is_the_middle_of_current_bounds(self) -> None:
        element = drv._parse_tree(_tree(_node("A", bounds="[10,20][30,60]")))[0]
        assert element.center == (20, 40)

    def test_label_prefers_text_then_desc_then_id(self) -> None:
        by_desc = drv._parse_tree(_tree(_node(desc="described")))[0]
        by_id = drv._parse_tree(_tree(_node(res="com.x:id/y")))[0]
        assert by_desc.label == "described"
        assert by_id.label == "com.x:id/y"

    def test_substring_match_is_case_insensitive(self) -> None:
        element = drv._parse_tree(_tree(_node("Connect Firebase")))[0]
        assert element.matches("connect")
        assert not element.matches("connect", exact=True)
        assert element.matches("Connect Firebase", exact=True)

    def test_str_names_the_element_and_its_centre(self) -> None:
        element = drv._parse_tree(
            _tree(_node("Go", cls="android.widget.Button", bounds="[0,0][10,10]"))
        )[0]
        assert str(element) == "'Go' <Button> at (5,5)"


class TestFind:
    def test_returns_the_single_match(self, ui: Harness) -> None:
        ui.device.trees = [_tree(_node("Alpha"), _node("Beta"), _node("Gamma"))]
        assert ui.ui.find("Beta").text == "Beta"

    def test_missing_element_raises_and_names_what_is_on_screen(
        self, ui: Harness
    ) -> None:
        ui.device.trees = [_tree(_node("Alpha"), _node("Beta"), _node("Gamma"))]
        with pytest.raises(drv.ElementNotFoundError, match="Alpha"):
            ui.ui.find("Nope")

    def test_ambiguity_is_an_error_not_a_first_match(self, ui: Harness) -> None:
        # `tap "Back"` must not silently hit "OFFLINE BACKUP".
        ui.device.trees = [_tree(_node("Back"), _node("OFFLINE BACKUP"))]
        with pytest.raises(drv.AmbiguousElementError, match="2 elements"):
            ui.ui.find("Back")

    def test_exact_disambiguates(self, ui: Harness) -> None:
        ui.device.trees = [_tree(_node("Back"), _node("OFFLINE BACKUP"))]
        assert ui.ui.find("Back", exact=True).text == "Back"


class TestDump:
    def test_retries_while_the_tree_looks_partial(self, ui: Harness) -> None:
        # Flutter reports only the focused EditText while the keyboard is up.
        partial = _tree(_node(cls="android.widget.EditText"))
        full = _tree(*[_node(f"n{i}") for i in range(8)])
        ui.device.trees = [partial, partial, full]
        assert len(ui.ui.dump()) == 8

    def test_returns_the_best_seen_when_every_retry_is_partial(
        self, ui: Harness
    ) -> None:
        ui.device.trees = [_tree(), _tree(_node("only"))]
        assert [e.text for e in ui.ui.dump()] == ["only"]


class TestWaitFor:
    def test_polls_until_the_element_appears(self, ui: Harness) -> None:
        ui.device.trees = [_tree(_node("nope")), _tree(_node("Connected."))]
        assert ui.ui.wait_for("Connected.", timeout=5).text == "Connected."

    def test_times_out_with_the_last_reason(self, ui: Harness) -> None:
        ui.device.trees = [_tree(_node("nope"))]
        with pytest.raises(drv.ElementNotFoundError, match="waited"):
            ui.ui.wait_for("Connected.", timeout=0.01)


class TestTap:
    def test_taps_the_centre_of_the_resolved_element(self, ui: Harness) -> None:
        ui.device.trees = [_tree(_node("Go", bounds="[100,200][300,400]"))]
        ui.ui.tap("Go")
        assert ui.device.taps() == [(200, 300)]

    def test_closes_the_keyboard_before_tapping(self, ui: Harness) -> None:
        # The tree reports a widget's LAID-OUT position even when the keyboard
        # covers it, so tapping blind lands on a letter key.
        ui.device.keyboard_shown = True
        ui.device.trees = [_tree(_node("Go", bounds="[0,0][100,100]"))]
        ui.ui.tap("Go")
        keyevents = [
            c for c in ui.device.calls if c[:3] == ("shell", "input", "keyevent")
        ]
        assert keyevents, "expected the keyboard to be dismissed first"


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
