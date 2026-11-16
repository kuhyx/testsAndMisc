"""Tests for :mod:`python_pkg.android_ui.workout_firebase_flow`.

The driver is a mock: what is under test is the flow's decisions (already
connected, account chooser, credential screen, timeout) and its exit codes,
not adb. No real device is touched.
"""

from __future__ import annotations

import runpy
import sys
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from fastmcp.exceptions import ToolError
import pytest

from python_pkg.android_ui import workout_firebase_flow as flow
from python_pkg.android_ui.driver import ElementNotFoundError, UiElement

if TYPE_CHECKING:
    from collections.abc import Iterator

MOD = "python_pkg.android_ui.workout_firebase_flow"
TARGET = "python_pkg.android_ui._mcp_target"
_CHOOSER_ID = "com.google.android.gms:id/google_sign_in_container"


@pytest.fixture(autouse=True)
def _no_sleep() -> Iterator[None]:
    with patch(f"{MOD}.time.sleep"):
        yield


def _el(
    text: str = "", *, cls: str = "android.widget.TextView", **kw: str
) -> UiElement:
    """Build one element; ``hint``/``res``/``desc`` override the empty defaults."""
    return UiElement(
        text=text,
        content_desc=kw.get("desc", ""),
        resource_id=kw.get("res", ""),
        class_name=cls,
        bounds=(0, 0, 100, 50),
        enabled=True,
        focused=False,
        hint=kw.get("hint", ""),
    )


def _ui(*screens: list[UiElement]) -> MagicMock:
    """A driver whose successive dumps return ``screens`` (last one repeats)."""
    ui = MagicMock()
    seq = list(screens)
    ui.dump.side_effect = lambda: seq.pop(0) if len(seq) > 1 else seq[0]
    return ui


CONNECTED = [_el("Disconnect"), _el("Connected to Firebase.")]
SIGN_IN = [_el("Sign in with Google")]


class TestFlow:
    def test_navigates_by_label_and_connects(self) -> None:
        ui = _ui(SIGN_IN, SIGN_IN, CONNECTED)
        assert flow.run_flow(ui, account=None, timeout=5) == "connected"
        taps = [c.args[0] for c in ui.tap.call_args_list]
        assert taps == [flow.SETTINGS, flow.SYNC_ROW, flow.SIGN_IN]
        ui.scroll_to.assert_called_once_with(flow.SYNC_ROW)

    def test_backs_out_of_a_workout_to_home_before_settings(self) -> None:
        # The app reopens into an in-progress workout, which has no gear.
        ui = _ui(CONNECTED)
        ui.find_all.side_effect = [[], [], [_el(desc="Settings")]]
        flow.run_flow(ui, account=None, timeout=5)
        assert ui.back.call_count == 2
        ui.find_all.assert_called_with(flow.SETTINGS, exact=True)

    def test_gives_up_backing_out_and_lets_the_tap_name_settings(self) -> None:
        ui = _ui(CONNECTED)
        ui.find_all.return_value = []
        ui.tap.side_effect = ElementNotFoundError("no element matches 'Settings'")
        with pytest.raises(ElementNotFoundError, match="Settings"):
            flow.run_flow(ui, account=None, timeout=5)
        assert ui.back.call_count == flow.MAX_BACKS

    def test_already_connected_taps_nothing_on_the_sync_screen(self) -> None:
        ui = _ui(CONNECTED)
        assert flow.run_flow(ui, account=None, timeout=5) == "already connected"
        assert flow.SIGN_IN not in [c.args[0] for c in ui.tap.call_args_list]

    def test_account_chooser_picks_the_given_account(self) -> None:
        # As the Pixel shows it: a Polish title, so only the GMS id is stable.
        chooser = [_el("Wybierz konto", res=_CHOOSER_ID), _el("me@example.com")]
        ui = _ui(SIGN_IN, chooser, CONNECTED)
        assert flow.run_flow(ui, account="me@example.com", timeout=5) == "connected"
        ui.tap.assert_called_with("me@example.com", exact=True)

    def test_account_manager_chooser_picks_account_then_confirms(self) -> None:
        """Android's AccountManager picker: a checked list plus an OK button."""
        picker = [
            _el("Wybierz konto"),
            _el("me@example.com", cls="android.widget.CheckedTextView"),
            _el("OK", cls="android.widget.Button", res="android:id/button2"),
        ]
        ui = _ui(SIGN_IN, picker, picker, CONNECTED)
        assert flow.run_flow(ui, account="me@example.com", timeout=5) == "connected"
        taps = [c.args[0] for c in ui.tap.call_args_list]
        assert taps[-2:] == ["me@example.com", "android:id/button2"]

    def test_picker_closed_by_the_account_tap_is_not_confirmed(self) -> None:
        picker = [_el("me@example.com", cls="android.widget.CheckedTextView")]
        ui = _ui(SIGN_IN, picker, [], CONNECTED)
        assert flow.run_flow(ui, account="me@example.com", timeout=5) == "connected"
        taps = [c.args[0] for c in ui.tap.call_args_list]
        assert taps[-1] == "me@example.com"

    def test_account_manager_chooser_without_account_hands_over(self) -> None:
        picker = [_el("me@example.com", cls="android.widget.CheckedTextView")]
        ui = _ui(SIGN_IN, picker)
        with pytest.raises(flow.HandOverError, match="--account"):
            flow.run_flow(ui, account=None, timeout=5)

    def test_account_chooser_without_account_hands_over(self) -> None:
        ui = _ui(SIGN_IN, [_el("Wybierz konto", res=_CHOOSER_ID)])
        with pytest.raises(flow.HandOverError, match="--account"):
            flow.run_flow(ui, account=None, timeout=5)

    def test_password_field_hands_over_and_types_nothing(self) -> None:
        pw = [_el(cls="android.widget.EditText", hint="Enter your password")]
        ui = _ui(SIGN_IN, pw)
        with pytest.raises(flow.HandOverError, match="secret"):
            flow.run_flow(ui, account=None, timeout=5)
        ui.type_into.assert_not_called()
        ui.type_into_field.assert_not_called()

    def test_non_secret_text_field_does_not_hand_over(self) -> None:
        email = [_el(cls="android.widget.EditText", hint="Email or phone")]
        ui = _ui(SIGN_IN, email, CONNECTED)
        assert flow.run_flow(ui, account=None, timeout=5) == "connected"

    def test_never_connecting_times_out_naming_the_query(self) -> None:
        ui = _ui(SIGN_IN)
        with (
            patch(f"{MOD}.time.monotonic", side_effect=[0.0, 0.0, 99.0]),
            pytest.raises(ElementNotFoundError, match="Disconnect"),
        ):
            flow.run_flow(ui, account=None, timeout=5)


class TestMain:
    def test_success_exits_zero(self, capsys: pytest.CaptureFixture[str]) -> None:
        with (
            patch(f"{MOD}.connect") as connect,
            patch(f"{MOD}.run_flow", return_value="connected"),
        ):
            assert flow.main(["--serial", "PIX", "--display", "0"]) == 0
        connect.assert_called_once_with("PIX", "0", "workout-firebase-flow")
        assert "connected" in capsys.readouterr().out

    def test_negative_step_exits_nonzero_naming_the_query(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        ui = MagicMock()
        ui.tap.side_effect = ElementNotFoundError("no element matches 'No Such Button'")
        with patch(f"{MOD}.connect", return_value=ui):
            assert flow.main(["--negative"]) == 1
        ui.tap.assert_called_once_with(flow.NEGATIVE, exact=True, timeout=3.0)
        assert "No Such Button" in capsys.readouterr().err

    def test_bad_target_exits_four(self, capsys: pytest.CaptureFixture[str]) -> None:
        with patch(f"{MOD}.connect", side_effect=ToolError("2 devices attached")):
            assert flow.main([]) == flow.EXIT_TARGET
        assert "2 devices attached" in capsys.readouterr().err

    def test_hand_over_exits_six(self, capsys: pytest.CaptureFixture[str]) -> None:
        with (
            patch(f"{MOD}.connect"),
            patch(f"{MOD}.run_flow", side_effect=flow.HandOverError("secret")),
        ):
            assert flow.main([]) == flow.EXIT_HAND_OVER
        assert "take over" in capsys.readouterr().err

    def test_negative_button_that_exists_still_fails(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        with patch(f"{MOD}.connect", return_value=MagicMock()):
            assert flow.main(["--negative"]) == flow.EXIT_ELEMENT
        assert "No Such Button" in capsys.readouterr().err

    def test_module_entry_point_exits_with_main(self) -> None:
        # patch.dict restores the original module afterwards, so the ``flow``
        # imported above stays the one later tests patch.
        with (
            patch.dict(sys.modules),
            patch.object(sys, "argv", ["workout-firebase-flow"]),
            patch(f"{TARGET}.connect", side_effect=ToolError("no phone")),
        ):
            sys.modules.pop(MOD)
            with pytest.raises(SystemExit) as caught:
                runpy.run_module(MOD, run_name="__main__")
        assert caught.value.code == flow.EXIT_TARGET
