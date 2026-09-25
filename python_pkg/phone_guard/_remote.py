"""Per-tool rules for ``adb shell`` commands, for :mod:`classify`.

Split out of ``classify.py`` for the 250-line cap. Each handler takes the
remote command's arguments (after the tool name) and returns the
:class:`~python_pkg.phone_guard.classify.Need` without a serial; the caller
stamps the serial on.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from python_pkg.phone_guard._need import SCREEN, WHOLE_PHONE, Need

if TYPE_CHECKING:
    from collections.abc import Callable

_PM_PACKAGE = {
    "clear",
    "uninstall",
    "disable",
    "disable-user",
    "enable",
    "hide",
    "unhide",
    "suspend",
    "unsuspend",
    "grant",
    "revoke",
}
_IDLE_WRITE = {"force-idle", "step", "unforce", "enable", "disable", "force-inactive"}
# `cmd connectivity set-package-networking-enabled <bool> <package>`
_NETWORKING_PKG_INDEX = 3


def _display_flag(args: list[str], flag: str) -> int | None:
    if flag in args:
        i = args.index(flag)
        if i + 1 < len(args) and args[i + 1].isdigit():
            return int(args[i + 1])
    return None


# `pm` options that take a value, so the value is not mistaken for the package.
_PM_VALUED = {"--user", "-u"}


def _package_after(args: list[str], verb: str) -> str | None:
    rest = args[args.index(verb) + 1 :]
    i = 0
    while i < len(rest):
        if rest[i] in _PM_VALUED:
            i += 2
        elif rest[i].startswith("-"):
            i += 1
        else:
            return rest[i]
    return None


def _am(rest: list[str]) -> Need:
    first = rest[0] if rest else ""
    if first in {"force-stop", "kill", "stop-app"} and len(rest) > 1:
        return Need(scope=f"pkg:{rest[-1]}")
    if first in {"start", "start-activity", "startservice", "start-foreground-service"}:
        display = _display_flag(rest, "--display")
        return Need(display=display) if display else Need(scope=SCREEN)
    return Need()


def _pm(rest: list[str]) -> Need:
    if not rest or rest[0] not in _PM_PACKAGE:
        return Need()
    package = _package_after(rest, rest[0])
    return Need(scope=f"pkg:{package}" if package else SCREEN)


def _cmd(rest: list[str]) -> Need:
    if rest[:2] != ["connectivity", "set-package-networking-enabled"]:
        is_set = (
            rest[:1] == ["connectivity"]
            and rest[1:2] != []
            and rest[1].startswith(("set-", "airplane-mode"))
        )
        return Need(scope=WHOLE_PHONE) if is_set else Need()
    package = rest[3] if len(rest) > _NETWORKING_PKG_INDEX else None
    return Need(scope=f"pkg:{package}") if package else Need(scope=WHOLE_PHONE)


def _dumpsys(rest: list[str]) -> Need:
    writes = (rest[:1] == ["deviceidle"] and rest[1:2] and rest[1] in _IDLE_WRITE) or (
        rest[:1] == ["battery"] and rest[1:2] and rest[1] in {"set", "unplug", "reset"}
    )
    return Need(scope=WHOLE_PHONE) if writes else Need()


def _settings(rest: list[str]) -> Need:
    return Need(scope=WHOLE_PHONE) if rest[:1] == ["put"] else Need()


def _wm(rest: list[str]) -> Need:
    changes = rest[:1] in (["size"], ["density"]) and len(rest) > 1
    return Need(scope=SCREEN) if changes else Need()


REMOTE: dict[str, Callable[[list[str]], Need]] = {
    "am": _am,
    "pm": _pm,
    "cmd": _cmd,
    "dumpsys": _dumpsys,
    "settings": _settings,
    "wm": _wm,
    "monkey": lambda _rest: Need(scope=SCREEN),
    "svc": lambda _rest: Need(scope=WHOLE_PHONE),
    "reboot": lambda _rest: Need(scope=WHOLE_PHONE),
    "setprop": lambda _rest: Need(scope=WHOLE_PHONE),
    "stop": lambda _rest: Need(scope=WHOLE_PHONE),
    "start": lambda _rest: Need(scope=WHOLE_PHONE),
}
