"""Device, display and lease resolution for :mod:`python_pkg.android_ui.mcp_server`.

The same rules as the CLI (:func:`python_pkg.android_ui.cli._target` is reused
as-is), with two MCP-specific differences:

* the default display is ``"self"`` rather than the real screen, so an agent
  drives its own ``phone_vd.sh`` display unless it asks for display 0; and
* with several devices and no serial the error names every serial, because
  an agent can only pick one if it is told what there is to pick from.

Every failure is a :class:`~fastmcp.exceptions.ToolError`, which FastMCP
returns as an ``isError`` result with this message unmasked.
"""

from __future__ import annotations

import re
import shutil
import subprocess

from fastmcp.exceptions import ToolError

from python_pkg.android_ui._elements import _escape
from python_pkg.android_ui.cli import _target, _TargetError
from python_pkg.android_ui.driver import AndroidUi
from python_pkg.phone_lease import (
    NoPhoneError,
    PhoneBusyError,
    acquire,
    resolve_serial,
)

_ADB_DEVICES_TIMEOUT_S = 10.0
_REDACTED = "<typed text redacted>"
# The driver's adb error names the failed command, and for typing that command
# is `input -d N text <the text>`: cut everything after `text` on that line.
_INPUT_TEXT = re.compile(r"(input -d \S+ text ).*")


def attached_serials() -> list[str]:
    """Return the serials ``adb devices`` reports as ready, in its order."""
    adb = shutil.which("adb")
    if adb is None:
        return []
    try:
        done = subprocess.run(
            [adb, "devices"],
            capture_output=True,
            text=True,
            timeout=_ADB_DEVICES_TIMEOUT_S,
            check=False,
        )
    except OSError, subprocess.TimeoutExpired:
        return []
    serials = []
    for line in done.stdout.splitlines()[1:]:
        serial, _, state = line.partition("\t")
        if state == "device":
            serials.append(serial)
    return serials


def _resolve(serial: str | None) -> str:
    """Return the device to drive; never guess between several."""
    try:
        return resolve_serial(serial)
    except NoPhoneError as exc:
        found = attached_serials()
        if len(found) > 1:
            msg = (
                f"{len(found)} devices attached ({', '.join(found)}) and no "
                "serial given: pass serial=<one of them>; refusing to guess"
            )
            raise ToolError(msg) from exc
        raise ToolError(str(exc)) from exc


def connect(serial: str | None, display: str | int, command: str) -> AndroidUi:
    """Resolve device and display, take the lease, and return a driver.

    ``display`` is ``"self"`` (this session's virtual display), ``0`` / ``"0"``
    (the real screen), or a virtual display id this session owns. No virtual
    display is ever created here: a missing one is an error.
    """
    resolved = _resolve(serial)
    try:
        target, scope = _target(resolved, str(display))
    except _TargetError as exc:
        raise ToolError(str(exc)) from exc
    try:
        acquire(resolved, f"android_ui mcp {command}", scope=scope)
    except PhoneBusyError as exc:
        raise ToolError(str(exc)) from exc
    return AndroidUi(serial=resolved, display=target)


def redact(message: str, text: str) -> str:
    """Remove typed ``text`` from an error message, however it got there.

    The driver's own "unchanged" messages give only lengths, but an adb
    failure while typing quotes the command line. Never echo typed text: a
    "does this look like a password?" heuristic is one that can fail open.
    """
    if not text:
        return message
    cleaned = _INPUT_TEXT.sub(rf"\g<1>{_REDACTED}", message)
    for form in (_escape(text), text):
        cleaned = cleaned.replace(form, _REDACTED)
    return cleaned
