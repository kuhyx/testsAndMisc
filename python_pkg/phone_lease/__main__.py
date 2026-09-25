"""CLI: ``python3 -m python_pkg.phone_lease acquire|release|status|holds|reap``.

The serial is optional everywhere; see :func:`serial.resolve_serial`.
Scope flags: ``--package <pkg>`` (one app) or ``--whole-phone``; neither means
the real screen, which is what every caller meant before scopes existed.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import sys

from python_pkg.phone_lease.lease import (
    DEFAULT_TTL,
    DEFAULT_WAIT,
    PhoneBusyError,
    Terms,
    acquire,
    scope_of,
)
from python_pkg.phone_lease.ops import holds, reap, release, status_all
from python_pkg.phone_lease.owner import owner_id
from python_pkg.phone_lease.serial import NoPhoneError, resolve_serial


def _scoped(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("serial", nargs="?", default=None)
    which = parser.add_mutually_exclusive_group()
    which.add_argument("--package", default=None, help="lease one app only")
    which.add_argument(
        "--whole-phone",
        action="store_true",
        help="phone-wide changes (Doze, sleep, reboot); capped at 300 s",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="phone-lease", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    take = sub.add_parser(
        "acquire", help="take or refresh a lease (exit 3 when held elsewhere)"
    )
    _scoped(take)
    take.add_argument(
        "--note", default="", help="what the holder is doing, shown to the other side"
    )
    take.add_argument("--ttl", type=float, default=DEFAULT_TTL)
    take.add_argument("--wait", type=float, default=DEFAULT_WAIT)
    take.add_argument(
        "--cleanup",
        action="append",
        default=[],
        help="command to run once on release or expiry (repeatable)",
    )
    _scoped(sub.add_parser("release", help="drop a lease this session holds"))
    look = sub.add_parser("status", help="list live leases, or 'free'")
    look.add_argument("serial", nargs="?", default=None)
    look.add_argument("--json", action="store_true", help="machine-readable list")
    ask = sub.add_parser("holds", help="exit 0 if OWNER may act on the scope")
    _scoped(ask)
    ask.add_argument("--owner", default=None, help="defaults to this session")
    sub.add_parser("whoami", help="print this session's owner id")
    reaper = sub.add_parser("reap", help="internal: run cleanup when a lease expires")
    reaper.add_argument("serial")
    reaper.add_argument("--owner", required=True)
    reaper.add_argument("--scope", required=True)
    return parser


def _run(args: argparse.Namespace) -> int:
    if args.command == "whoami":
        sys.stdout.write(f"{owner_id()}\n")
        return 0
    if args.command == "reap":
        reap(args.serial, args.owner, args.scope)
        return 0
    serial = resolve_serial(args.serial)
    if args.command == "status":
        live = status_all(serial)
        if args.json:
            sys.stdout.write(json.dumps([asdict(x) for x in live]) + "\n")
        else:
            lines = [x.describe() for x in live] or ["free"]
            sys.stdout.write("\n".join(lines) + "\n")
        return 0
    scope = scope_of(args.package, whole_phone=args.whole_phone)
    if args.command == "holds":
        return 0 if holds(serial, args.owner or owner_id(), scope) else 1
    if args.command == "release":
        dropped = release(serial, scope=scope)
        sys.stdout.write("released\n" if dropped else f"not held by {owner_id()}\n")
        return 0 if dropped else 1
    terms = Terms(ttl=args.ttl, wait=args.wait, cleanup=tuple(args.cleanup))
    lease = acquire(serial, args.note, scope=scope, terms=terms)
    sys.stdout.write(f"{lease.describe()}\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the CLI. Exit 0 ok, 1 not held, 3 held elsewhere, 4 no phone."""
    args = _build_parser().parse_args(argv)
    try:
        return _run(args)
    except PhoneBusyError as exc:
        sys.stderr.write(f"phone-lease: {exc}\n")
        return 3
    except NoPhoneError as exc:
        sys.stderr.write(f"phone-lease: {exc}\n")
        return 4


if __name__ == "__main__":
    sys.exit(main())
