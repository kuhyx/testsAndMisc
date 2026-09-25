"""Which phone a call is about, resolved the same way by every caller.

Before this existed android_ui leased the literal key ``default`` while
phone_deploy leased the real serial, so the two never saw each other and
drove the same phone at once (2026-09-25).
"""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

_ENV_KEYS = ("ANDROID_SERIAL", "ADB_SERIAL")


class NoPhoneError(RuntimeError):
    """Raised when no serial is given and adb cannot name exactly one phone."""


def _adb_serial() -> str:
    adb = shutil.which("adb")
    if adb is None:
        return ""
    done = subprocess.run(
        [adb, "get-serialno"],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return done.stdout.strip() if done.returncode == 0 else ""


def resolve_serial(
    explicit: str | None = None,
    *,
    environ: Mapping[str, str] | None = None,
    ask_adb: Callable[[], str] | None = None,
) -> str:
    """``explicit``, else $ANDROID_SERIAL / $ADB_SERIAL, else ``adb get-serialno``."""
    if explicit:
        return explicit
    env = os.environ if environ is None else environ
    for key in _ENV_KEYS:
        if env.get(key):
            return env[key]
    try:
        found = (ask_adb or _adb_serial)()
    except OSError, subprocess.TimeoutExpired:
        found = ""
    if not found or found == "unknown":
        msg = (
            "no phone serial: pass one, set ANDROID_SERIAL, or connect exactly "
            "one device (adb get-serialno found none or several)"
        )
        raise NoPhoneError(msg)
    return found
