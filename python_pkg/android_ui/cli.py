"""Command line for :mod:`python_pkg.android_ui`.

Every subcommand exits non-zero and names the query when an element is missing
or ambiguous, so a shell script (or an agent) can tell a real failure from a
successful no-op instead of guessing from a screenshot.

    android-ui dump
    android-ui find "Connect Firebase"
    android-ui tap "Connect Firebase"
    android-ui type "Sync account email" kuhy@example.com
    android-ui wait "Connected to Firebase." --timeout 30
"""

from __future__ import annotations

import argparse
import sys

from python_pkg.android_ui.driver import AndroidUi, UiAutomationError


def _build_parser() -> argparse.ArgumentParser:
    """Return the argument parser for the ``android-ui`` command."""
    parser = argparse.ArgumentParser(
        prog="android-ui",
        description="Drive an Android app by element, never by coordinates.",
    )
    parser.add_argument("-s", "--serial", help="target device serial")
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


def main(argv: list[str] | None = None) -> int:
    """Run the CLI. Returns a process exit code."""
    args = _build_parser().parse_args(argv)
    ui = AndroidUi(serial=args.serial)

    try:
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
