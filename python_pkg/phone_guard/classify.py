"""Decide what a shell command's ``adb`` calls need before they may run.

Pure: no adb, no filesystem. The hook feeds it the Bash tool's command and
applies the answer. Every ``adb`` invocation in the command gets one
:class:`Need`:

* nothing -- reads (``logcat``, ``dumpsys``, ``getprop``, ``pull``,
  ``screencap``), file transfer, and anything aimed at the caller's own
  virtual display;
* a lease on the real screen -- input or launches on display 0;
* a lease on one app -- ``force-stop``, ``install``, per-app network cuts;
* the whole-phone lease -- reboot, Wi-Fi/airplane/Doze/battery tricks,
  ``settings put``: everything that changes the phone for every session;
* a block -- key/text input without ``-d`` (it goes to whichever display last
  took focus, i.e. possibly another session's app), or input aimed at another
  session's virtual display.

Unknown commands pass: this guards against interrupting other sessions, it is
not a sandbox.
"""

from __future__ import annotations

import re
import shlex

from python_pkg.phone_guard._need import SCREEN, WHOLE_PHONE, Need
from python_pkg.phone_guard._remote import REMOTE, _display_flag

_SEPARATORS = {";", "&&", "||", "|", "&", "(", ")", "\n"}
_GLOBAL_WITH_ARG = {"-s", "-t", "-H", "-P", "-L"}
_HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1[^\n]*\n.*?\n\s*\2\s*(?=\n|$)", re.DOTALL)

_WHOLE_PHONE_ADB = {
    "reboot",
    "root",
    "unroot",
    "remount",
    "disable-verity",
    "enable-verity",
    "tcpip",
    "usb",
    "kill-server",
    "sideload",
}
_READ_ADB = {
    "devices",
    "get-serialno",
    "get-state",
    "version",
    "help",
    "logcat",
    "pull",
    "push",
    "wait-for-device",
    "forward",
    "reverse",
    "bugreport",
    "start-server",
    "sync",
}
_KEYS = {"text", "keyevent", "keycombination"}
_POINTER = {"tap", "swipe", "draganddrop", "press", "roll", "motionevent", "scroll"}


def _tokens(command: str) -> list[str]:
    """Shell tokens, heredoc bodies removed (a script being WRITTEN is not run)."""
    lexer = shlex.shlex(
        _HEREDOC.sub("\n", command), posix=True, punctuation_chars=";&|()"
    )
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    try:
        return list(lexer)
    except ValueError:
        return []


def _split(tokens: list[str]) -> list[list[str]]:
    """Split a token stream into simple commands."""
    groups: list[list[str]] = [[]]
    for word in tokens:
        if word in _SEPARATORS or set(word) <= set(";&|"):
            groups.append([])
        else:
            groups[-1].append(word)
    return [g for g in groups if g]


def adb_calls(command: str) -> list[list[str]]:
    """Every ``adb ...`` simple command, as its argument list (no ``adb``)."""
    calls = []
    for simple in _split(_tokens(command)):
        for i, word in enumerate(simple):
            if word == "adb" or word.endswith("/adb"):
                calls.append(simple[i + 1 :])
                break
    return calls


def _input(args: list[str], serial: str | None) -> Need:
    display = _display_flag(args, "-d")
    verb = next((a for a in args if a in _KEYS | _POINTER), "")
    if display is not None and display != 0:
        return Need(display=display, serial=serial)
    if display is None and verb in _KEYS:
        return Need(
            block=f"`input {verb}` without -d goes to whichever display last took "
            "focus -- possibly another session's app. Add `-d 0` for the real "
            "screen or `-d <your display>` (phone_vd.sh id).",
            serial=serial,
        )
    return Need(scope=SCREEN, serial=serial)


def _remote(args: list[str], serial: str | None) -> list[Need]:
    """Needs of one ``adb shell`` command line."""
    found = []
    for simple in _split(_tokens(" ".join(args))):
        tool, rest = simple[0], simple[1:]
        found.append(_remote_one(tool, rest, serial))
    return found


def _remote_one(tool: str, rest: list[str], serial: str | None) -> Need:
    """The need of one remote command, stamped with the call's serial."""
    if tool == "input":
        return _input(rest, serial)
    need = REMOTE.get(tool, lambda _rest: Need())(rest)
    return Need(scope=need.scope, block=need.block, display=need.display, serial=serial)


def needs(command: str, apk_package: dict[str, str] | None = None) -> list[Need]:
    """Every adb call's :class:`Need` in ``command``.

    ``apk_package`` maps an APK path to its package, resolved by the caller
    (reading an APK is I/O); an unknown APK's install needs the screen.
    """
    known = apk_package or {}
    result: list[Need] = []
    for call in adb_calls(command):
        serial = None
        i = 0
        while i < len(call) and call[i].startswith("-"):
            if call[i] in _GLOBAL_WITH_ARG and i + 1 < len(call):
                serial = call[i + 1] if call[i] == "-s" else serial
                i += 2
            else:
                i += 1
        sub, args = (call[i], call[i + 1 :]) if i < len(call) else ("", [])
        if sub in {"shell", "exec-out"}:
            result.extend(_remote(args, serial))
        elif sub in _WHOLE_PHONE_ADB:
            result.append(Need(scope=WHOLE_PHONE, serial=serial))
        elif sub in {"install", "install-multiple", "uninstall"}:
            target = next((a for a in reversed(args) if not a.startswith("-")), "")
            package = known.get(target) or (target if sub == "uninstall" else None)
            result.append(
                Need(scope=f"pkg:{package}" if package else SCREEN, serial=serial)
            )
        elif sub in _READ_ADB or not sub:
            result.append(Need(serial=serial))
        else:
            result.append(Need(serial=serial))
    return result
