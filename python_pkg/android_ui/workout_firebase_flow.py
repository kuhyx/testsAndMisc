"""Drive workout_app's "connect Firebase" flow by label, with no coordinates.

    python3 -m python_pkg.android_ui.workout_firebase_flow --serial 23181JEGR08034 \
        [--display self] [--account EMAIL]
    python3 -m python_pkg.android_ui.workout_firebase_flow --serial ... --negative

[BACK to Home] -> Settings (gear semanticLabel) -> scroll to the "Sync
settings" row -> Sync settings -> "Sign in with Google" -> wait for
"Disconnect". Every workout_app label lives in this file and nowhere else, so a
layout change (reordering the SYNC and OFFLINE BACKUP sections) needs no edit
here -- only a renamed label does, and then the run fails naming it.

Exit codes: 0 connected (or already was), 1 an element was missing or
ambiguous (stderr names the query), 4 bad device/display/lease, 6 a screen
wants a password, 2FA code or an account choice: a human takes over. It never
types anything; ``--negative`` taps a button that does not exist, to prove a
missing element exits non-zero.
"""

from __future__ import annotations

import argparse
import sys
import time
from typing import TYPE_CHECKING

from fastmcp.exceptions import ToolError

from python_pkg.android_ui._mcp_target import connect
from python_pkg.android_ui.driver import ElementNotFoundError, UiAutomationError

if TYPE_CHECKING:
    from python_pkg.android_ui.driver import AndroidUi, UiElement

# workout_app / sync_settings_ui labels (sync_settings_ui-v0.5.2).
SETTINGS = "Settings"  # home_screen.dart: the gear's tooltip
SYNC_ROW = "Sync settings"  # settings_screen_sections.dart: cloud icon semanticLabel
SIGN_IN = "Sign in with Google"
CONNECTED = "Disconnect"  # only rendered while Firebase is connected
# Google's account chooser: its title follows the phone's locale ("Wybierz
# konto" on the Pixel), so it is found by its GMS container id instead.
CHOOSER = "com.google.android.gms:id/google_sign_in_container"
# Android's AccountManager picker (seen 2026-11-16) has no GMS container: it is
# a checked list of account e-mails plus OK; tapping a row only checks it.
CHOOSER_ROW_CLASS = "CheckedTextView"
CHOOSER_OK = "android:id/button2"  # OK; button1 is Cancel (measured)
NEGATIVE = "No Such Button"
# Text that means a screen wants a secret. Matched on editable fields only, so
# a label such as "Use the account password instead" does not trip it.
_SECRET_MARKERS = ("password", "passcode", "verification code", "2-step", "pin")

EXIT_ELEMENT = 1
EXIT_TARGET = 4
EXIT_HAND_OVER = 6
_POLL_S = 1.0
# Routes stacked over Home when the app reopens (an in-progress workout, a
# summary); more than this means the app is somewhere unexpected.
MAX_BACKS = 3
_NEGATIVE_TIMEOUT_S = 3.0


class HandOverError(RuntimeError):
    """A screen needs a human: a secret, a 2FA code, or an account choice."""


def _connected(screen: list[UiElement]) -> bool:
    return any(e.matches(CONNECTED, exact=True) for e in screen)


def _asks_for_secret(screen: list[UiElement]) -> bool:
    for element in screen:
        if not element.class_name.endswith("EditText"):
            continue
        names = f"{element.hint} {element.content_desc} {element.resource_id}".lower()
        if any(marker in names for marker in _SECRET_MARKERS):
            return True
    return False


def _chooser_up(screen: list[UiElement]) -> bool:
    for element in screen:
        if element.matches(CHOOSER, exact=True):
            return True
        if element.class_name.endswith(CHOOSER_ROW_CLASS) and "@" in element.text:
            return True
    return False


def _reach_home(ui: AndroidUi) -> None:
    """Pop routes until Home's gear shows; the app may reopen mid-workout."""
    for _ in range(MAX_BACKS):
        if ui.find_all(SETTINGS, exact=True):
            return
        ui.back()


def run_flow(ui: AndroidUi, *, account: str | None, timeout: float) -> str:
    """Run the flow from wherever the app is; return how it ended."""
    _reach_home(ui)
    ui.tap(SETTINGS, exact=True)
    # Below the fold on a phone; scrolling to it is what makes the run survive
    # a section reorder without a coordinate.
    ui.scroll_to(SYNC_ROW)
    ui.tap(SYNC_ROW)
    if _connected(ui.dump()):
        return "already connected"
    ui.tap(SIGN_IN, exact=True)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        screen = ui.dump()
        if _connected(screen):
            return "connected"
        if _asks_for_secret(screen):
            msg = "the sign-in asks for a password or 2FA code (a secret)"
            raise HandOverError(msg)
        if _chooser_up(screen):
            if account is None:
                msg = "the Google account chooser is up: pass --account <email>"
                raise HandOverError(msg)
            ui.tap(account, exact=True)
            # A single tap closes some pickers; only confirm one still up.
            if any(e.matches(CHOOSER_OK, exact=True) for e in ui.dump()):
                ui.tap(CHOOSER_OK, exact=True)
        time.sleep(_POLL_S)
    msg = f"waited {timeout}s for {CONNECTED!r} after tapping {SIGN_IN!r}"
    raise ElementNotFoundError(msg)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="workout-firebase-flow")
    parser.add_argument("--serial", help="device serial (required with 2+ devices)")
    parser.add_argument(
        "--display", default="self", help="'self' (default) or 0 for the real screen"
    )
    parser.add_argument("--account", help="Google account to pick in the chooser")
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument(
        "--negative", action="store_true", help=f"tap {NEGATIVE!r} and fail"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the flow (or the negative step); return a process exit code."""
    args = _parser().parse_args(argv)
    try:
        ui = connect(args.serial, args.display, "workout-firebase-flow")
    except ToolError as exc:
        sys.stderr.write(f"workout-firebase-flow: {exc}\n")
        return EXIT_TARGET
    try:
        if args.negative:
            ui.tap(NEGATIVE, exact=True, timeout=_NEGATIVE_TIMEOUT_S)
            msg = f"negative step: {NEGATIVE!r} exists on screen, the check is void"
            raise ElementNotFoundError(msg)
        outcome = run_flow(ui, account=args.account, timeout=args.timeout)
    except UiAutomationError as exc:
        sys.stderr.write(f"workout-firebase-flow: {exc}\n")
        return EXIT_ELEMENT
    except HandOverError as exc:
        sys.stderr.write(f"workout-firebase-flow: {exc}; take over on the phone\n")
        return EXIT_HAND_OVER
    sys.stdout.write(f"workout-firebase-flow: {outcome}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
