"""PreToolUse hook: lease -- or refuse -- raw ``adb`` before the Bash tool runs it.

``android_ui``, ``phone_deploy.sh`` and ``phone_vd.sh`` take their own leases,
but a bare ``adb shell input tap`` in a Bash call took none, which is how one
session's tap landed in another session's app (2026-09-25). Claude Code pipes
the tool call here as JSON; exit 2 blocks it and shows stderr to the model.

Leases are taken as this session (``phone_lease.owner_id`` finds the
``claude`` ancestor), so a later ``android_ui`` call from the same session
simply refreshes them.
"""

from __future__ import annotations

import json
import subprocess
import sys
from typing import TYPE_CHECKING

from python_pkg.android_ui._a11y_helper import build_tool
from python_pkg.android_ui._elements import UiAutomationError
from python_pkg.phone_guard._need import SCREEN, WHOLE_PHONE
from python_pkg.phone_guard.classify import adb_calls, needs
from python_pkg.phone_guard.vd_state import display_owner, own_display
from python_pkg.phone_lease import (
    NoPhoneError,
    PhoneBusyError,
    Terms,
    acquire,
    owner_id,
    resolve_serial,
    scope_of,
)

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import TextIO

    from python_pkg.phone_guard._need import Need

BLOCK = 2
# Under Claude Code's 60 s hook timeout, with room to report.
_WAIT_SECONDS = 40.0


def _apk_packages(command: str) -> dict[str, str]:
    """Map each APK an ``adb install`` names to its package (via aapt2)."""
    found: dict[str, str] = {}
    try:
        aapt2 = str(build_tool("aapt2"))
    except UiAutomationError:
        return found  # no SDK: an unknown APK's install takes the screen lease
    for call in adb_calls(command):
        for word in call:
            if not word.endswith(".apk"):
                continue
            try:
                done = subprocess.run(
                    [aapt2, "dump", "packagename", word],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                )
            except OSError, subprocess.TimeoutExpired:
                continue
            if done.returncode == 0 and done.stdout.strip():
                found[word] = done.stdout.strip()
    return found


def _scope(need: Need, serial: str, owner: str) -> str:
    """The lease scope a need maps to; raises PermissionError for a foreign display."""
    if need.display is not None:
        mine = own_display(serial, owner)
        if mine is not None and mine.display == need.display:
            return scope_of(mine.package)
        other = display_owner(serial, need.display)
        whose = f"session {other.owner_dir}'s" if other else "not your"
        msg = (
            f"display {need.display} is {whose} virtual display; drive only "
            "your own (`phone_vd.sh id`)"
        )
        raise PermissionError(msg)
    if need.scope == SCREEN:
        return scope_of()
    if need.scope == WHOLE_PHONE:
        return scope_of(whole_phone=True)
    return str(need.scope)


def decide(command: str, note: str = "") -> str | None:
    """Take every lease ``command`` needs; return why it must not run, if so."""
    found: Iterable[Need] = needs(command, _apk_packages(command))
    owner = owner_id()
    for need in found:
        if need.block:
            return need.block
        if need.scope is None and need.display is None:
            continue
        try:
            serial = resolve_serial(need.serial)
        except NoPhoneError:
            continue  # no phone or several without -s: adb itself will refuse
        try:
            scope = _scope(need, serial, owner)
            acquire(
                serial,
                note or f"hook: {command[:60]}",
                scope=scope,
                terms=Terms(wait=_WAIT_SECONDS),
                owner=owner,
            )
        except PermissionError as exc:
            return str(exc)
        except PhoneBusyError as exc:
            return (
                f"{exc} -- wait for it, use your own virtual display, or ask the user"
            )
    return None


def main(stdin: TextIO | None = None) -> int:
    """Hook entry point: 0 lets the Bash call run, 2 blocks it."""
    try:
        payload = json.load(stdin or sys.stdin)
    except json.JSONDecodeError:
        return 0
    if payload.get("tool_name") != "Bash":
        return 0
    command = str((payload.get("tool_input") or {}).get("command") or "")
    if "adb" not in command:
        return 0
    reason = decide(command)
    if reason is None:
        return 0
    sys.stderr.write(f"phone_guard: {reason}\n")
    return BLOCK
