"""Command line entry point for the SyncYomi integrity guard.

Exit codes are the contract; a systemd timer and a human both read them:

* ``0`` — payload healthy (or a first-run baseline was recorded)
* ``1`` — payload collapsed, or it could not be read or decoded

A read failure is deliberately *not* a pass. The whole point of the guard is to
be believed on the day something is wrong, and "the database was missing so I
said OK" is the fail-open shape that lets a bad copy become the only copy.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess
import sys

from python_pkg.syncyomi_guard.payload import PayloadError, decode_payload
from python_pkg.syncyomi_guard.store import (
    StoreError,
    load_baseline,
    read_payload,
    save_baseline,
    write_snapshot,
)
from python_pkg.syncyomi_guard.verdict import Status, Thresholds, Verdict, compare

_DEFAULT_DB = Path("/home/kuhy/syncyomi/config/syncyomi.db")
_DEFAULT_STATE = Path.home() / ".local/share/syncyomi_guard"
_DEFAULT_SNAPSHOTS = Path.home() / "syncyomi/snapshots"
_DEFAULT_KEEP = 14


def _notify(title: str, body: str) -> None:
    """Best-effort desktop notification; never fails the run.

    The exit code is the real signal. A notification is a convenience, so a
    machine without ``notify-send`` (or a run with no session bus) must not turn
    a healthy check into a failure.
    """
    binary = shutil.which("notify-send")
    if binary is None:
        return
    try:
        subprocess.run(
            [binary, "--urgency=critical", title, body],
            check=False,
            timeout=10,
        )
    except OSError, subprocess.SubprocessError:
        return


def _build_parser() -> argparse.ArgumentParser:
    """Construct the argument parser."""
    parser = argparse.ArgumentParser(
        prog="syncyomi-guard",
        description=(
            "Verify the SyncYomi library payload has not silently collapsed, "
            "and snapshot it as a restorable .tachibk when it is healthy."
        ),
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=_DEFAULT_DB,
        help=f"SyncYomi SQLite database (default: {_DEFAULT_DB})",
    )
    parser.add_argument(
        "--state-dir",
        type=Path,
        default=_DEFAULT_STATE,
        help=f"where the baseline is stored (default: {_DEFAULT_STATE})",
    )
    parser.add_argument(
        "--snapshot-dir",
        type=Path,
        default=_DEFAULT_SNAPSHOTS,
        help=f"where .tachibk snapshots are written (default: {_DEFAULT_SNAPSHOTS})",
    )
    parser.add_argument(
        "--keep",
        type=int,
        default=_DEFAULT_KEEP,
        help=f"how many snapshots to retain (default: {_DEFAULT_KEEP})",
    )
    parser.add_argument(
        "--max-drop",
        type=float,
        default=Thresholds().max_drop_ratio,
        help="fail if any count drops by more than this fraction (default: 0.10)",
    )
    parser.add_argument(
        "--no-snapshot",
        action="store_true",
        help="check only; do not write a snapshot or update the baseline",
    )
    parser.add_argument(
        "--accept",
        action="store_true",
        help=(
            "record the current payload as the new baseline even if it looks "
            "collapsed (use after a deliberate library purge)"
        ),
    )
    return parser


def _report(verdict: Verdict) -> None:
    """Write the verdict to the appropriate stream.

    A silent guard is a useless one: the journal line is how a human finds out
    what the timer saw, so the counts are written on every run, not only on
    failures.
    """
    if verdict.is_failure:
        sys.stderr.write(f"COLLAPSED: {verdict.reason}\n")
        if verdict.previous is not None:
            sys.stderr.write(f"  previous: {verdict.previous.describe()}\n")
        sys.stderr.write(f"  current:  {verdict.current.describe()}\n")
    elif verdict.status is Status.FIRST_RUN:
        sys.stdout.write(f"baseline recorded: {verdict.current.describe()}\n")
    else:
        sys.stdout.write(f"ok: {verdict.reason}\n")


def main(argv: list[str] | None = None) -> int:
    """Run the guard, returning the process exit code."""
    args = _build_parser().parse_args(argv)

    try:
        blob = read_payload(args.db)
        stats = decode_payload(blob)
    except (StoreError, PayloadError) as exc:
        sys.stderr.write(f"FAILED: {exc}\n")
        _notify("SyncYomi guard: cannot verify", str(exc))
        return 1

    try:
        thresholds = Thresholds(max_drop_ratio=args.max_drop)
    except ValueError as exc:
        sys.stderr.write(f"FAILED: {exc}\n")
        return 1

    verdict = compare(stats, load_baseline(args.state_dir), thresholds)
    _report(verdict)

    if verdict.is_failure and not args.accept:
        _notify(
            "SyncYomi library collapsed",
            f"{verdict.reason}. Snapshot NOT overwritten; recover from "
            f"{args.snapshot_dir}.",
        )
        return 1

    if not args.no_snapshot:
        snapshot = write_snapshot(args.snapshot_dir, blob, args.keep)
        save_baseline(args.state_dir, stats)
        sys.stdout.write(f"snapshot: {snapshot}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
