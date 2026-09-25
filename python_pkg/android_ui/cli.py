"""Command line for :mod:`python_pkg.android_ui`.

Every subcommand exits non-zero and names the query when an element is missing
or ambiguous, so a shell script (or an agent) can tell a real failure from a
successful no-op instead of guessing from a screenshot.

    android-ui dump
    android-ui find "Connect Firebase"
    android-ui tap "Connect Firebase"
    android-ui type "Sync account email" kuhy@example.com
    android-ui wait "Connected to Firebase." --timeout 30
    android-ui --display self tap "Save"     # this session's phone_vd display
"""

from __future__ import annotations

import argparse
import sys

from python_pkg.android_ui.driver import AndroidUi, UiAutomationError
from python_pkg.phone_guard.vd_state import display_owner, own_display
from python_pkg.phone_lease import (
    NoPhoneError,
    PhoneBusyError,
    acquire,
    owner_id,
    resolve_serial,
    scope_of,
)

# Exit codes shared with phone_lease: 3 held elsewhere, 4 no phone.
_EXIT_BUSY = 3
_EXIT_NO_PHONE = 4
_EXIT_BAD_DISPLAY = 5


class _TargetError(RuntimeError):
    """The requested display cannot be driven by this session."""


def _build_parser() -> argparse.ArgumentParser:
    """Return the argument parser for the ``android-ui`` command."""
    parser = argparse.ArgumentParser(
        prog="android-ui",
        description="Drive an Android app by element, never by coordinates.",
    )
    parser.add_argument("-s", "--serial", help="target device serial")
    parser.add_argument(
        "--display",
        help="drive a virtual display instead of the real screen: its logical "
        "id, or 'self' for the one phone_vd.sh started for this session",
    )
    parser.add_argument(
        "--exact",
        action="store_true",
        help="require an exact label match instead of a substring",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("dump", help="list every labelled element on screen")

    for name, helptext in (
        ("find", "locate an element without touching it"),
        ("tap", "tap the element matching QUERY"),
        ("wait", "poll until QUERY appears"),
    ):
        cmd = sub.add_parser(name, help=helptext)
        cmd.add_argument("query")
        if name in {"tap", "wait"}:
            cmd.add_argument("--timeout", type=float, default=15.0)

    typed = sub.add_parser("type", help="type TEXT into the field at QUERY")
    typed.add_argument("query")
    typed.add_argument("text")
    typed.add_argument("--timeout", type=float, default=15.0)

    sub.add_parser("dismiss-keyboard", help="close the IME without popping the route")
    sub.add_parser("focus", help="print the currently focused window")
    return parser


def _target(serial: str, requested: str | None) -> tuple[int | None, str]:
    """Return (display, lease scope) for ``--display``.

    The real screen is shared, so it takes the screen lease. A virtual display
    must be this session's own (another session's app would be driven blind)
    and takes the lease on its app instead, which is what lets two sessions
    work at the same time.
    """
    if requested is None or requested == "0":
        return None, scope_of()  # the real screen: pkg:__screen__
    mine = own_display(serial, owner_id())
    if requested == "self":
        if mine is None:
            msg = "no virtual display for this session: run phone_vd.sh start <package>"
            raise _TargetError(msg)
        return mine.display, scope_of(mine.package)
    if not requested.isdigit():
        msg = f"--display takes a display id or 'self', not {requested!r}"
        raise _TargetError(msg)
    display = int(requested)
    if mine is None or mine.display != display:
        other = display_owner(serial, display)
        whose = f"owned by {other.owner_dir}" if other else "not this session's"
        msg = f"display {display} is {whose}; drive only your own (--display self)"
        raise _TargetError(msg)
    return display, scope_of(mine.package)


def _lease_phone(serial: str, command: str, scope: str) -> bool:
    """Refresh this session's lease; False when another session holds it.

    Keyed by the resolved serial, never a placeholder: serial-less calls used
    to lease "default" while phone_deploy leased the real serial, so neither
    saw the other and one session's tap landed in another's app (2026-09-25).
    """
    try:
        acquire(serial, f"android_ui {command}", scope=scope)
    except PhoneBusyError as exc:
        sys.stderr.write(f"android-ui: {exc}\n")
        return False
    return True


def _run(ui: AndroidUi, args: argparse.Namespace) -> None:
    """Dispatch one parsed command to the driver."""
    if args.command == "dump":
        for element in ui.dump():
            sys.stdout.write(f"{element}\n")
    elif args.command == "find":
        sys.stdout.write(f"{ui.find(args.query, exact=args.exact)}\n")
    elif args.command == "tap":
        found = ui.tap(args.query, exact=args.exact, timeout=args.timeout)
        sys.stdout.write(f"tapped {found}\n")
    elif args.command == "wait":
        found = ui.wait_for(args.query, timeout=args.timeout, exact=args.exact)
        sys.stdout.write(f"{found}\n")
    elif args.command == "type":
        ui.type_into(args.query, args.text, exact=args.exact, timeout=args.timeout)
        sys.stdout.write(f"typed into {args.query!r} and verified\n")
    elif args.command == "dismiss-keyboard":
        ui.dismiss_keyboard()
    elif args.command == "focus":
        sys.stdout.write(f"{ui.current_focus()}\n")


def main(argv: list[str] | None = None) -> int:
    """Run the CLI. Returns a process exit code."""
    args = _build_parser().parse_args(argv)
    try:
        serial = resolve_serial(args.serial)
        display, scope = _target(serial, args.display)
    except NoPhoneError as exc:
        sys.stderr.write(f"android-ui: {exc}\n")
        return _EXIT_NO_PHONE
    except _TargetError as exc:
        sys.stderr.write(f"android-ui: {exc}\n")
        return _EXIT_BAD_DISPLAY
    if not _lease_phone(serial, args.command, scope):
        return _EXIT_BUSY
    try:
        _run(AndroidUi(serial=serial, display=display), args)
    except UiAutomationError as exc:
        # Loud and non-zero on purpose: a silent no-op here is exactly the
        # failure this package exists to eliminate. The message already names
        # the query and what IS on screen, so print that rather than a
        # traceback -- "element not found" is an expected outcome, not a crash,
        # and a wall of stack frames buries the one line that helps.
        sys.stderr.write(f"android-ui: {exc}\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
