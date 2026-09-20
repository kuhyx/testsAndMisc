"""CLI: ``python3 -m python_pkg.phone_lease acquire|release|status <serial>``."""

from __future__ import annotations

import argparse
import sys

from python_pkg.phone_lease.lease import (
    DEFAULT_TTL,
    DEFAULT_WAIT,
    PhoneBusyError,
    acquire,
    owner_id,
    release,
    status,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="phone-lease", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    take = sub.add_parser(
        "acquire", help="take or refresh the lease (exit 3 when held elsewhere)"
    )
    take.add_argument("serial")
    take.add_argument(
        "--note", default="", help="what the holder is doing, shown to the other side"
    )
    take.add_argument("--ttl", type=float, default=DEFAULT_TTL)
    take.add_argument("--wait", type=float, default=DEFAULT_WAIT)
    drop = sub.add_parser("release", help="drop the lease if this session holds it")
    drop.add_argument("serial")
    look = sub.add_parser("status", help="print the holder, or 'free'")
    look.add_argument("serial")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI. Exit 0 ok, 1 nothing to release, 3 phone held elsewhere."""
    args = _build_parser().parse_args(argv)
    if args.command == "acquire":
        try:
            lease = acquire(args.serial, args.note, ttl=args.ttl, wait=args.wait)
        except PhoneBusyError as exc:
            sys.stderr.write(f"phone-lease: {exc}\n")
            return 3
        sys.stdout.write(f"{lease.describe()}\n")
        return 0
    if args.command == "release":
        dropped = release(args.serial)
        sys.stdout.write("released\n" if dropped else f"not held by {owner_id()}\n")
        return 0 if dropped else 1
    lease = status(args.serial)
    sys.stdout.write("free\n" if lease is None else f"{lease.describe()}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
