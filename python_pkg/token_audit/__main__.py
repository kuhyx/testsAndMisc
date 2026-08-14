"""Command-line entry point for the token audit.

Fails closed. If the per-axis rollup does not reconcile with the raw usage
figures the API reported, the run exits non-zero instead of printing a report
that quietly lost or double-counted sessions — a plausible-looking wrong number
is worse than no number, because it gets acted on.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
from typing import TYPE_CHECKING

from python_pkg.token_audit import attribute, imagecost, parse, report

if TYPE_CHECKING:
    from python_pkg.token_audit.model import Session

TRANSCRIPT_ROOT = Path.home() / ".claude" / "projects"
DEFAULT_DAYS = 7
SECONDS_PER_DAY = 86400
# Largest acceptable relative gap between the axis rollup and the raw usage
# totals. The two are computed independently, so anything above rounding noise
# means a session was mis-attributed.
MAX_DRIFT = 0.01
EXIT_DRIFT = 2
EXIT_NO_DATA = 3


def _build_parser() -> argparse.ArgumentParser:
    """Define the CLI surface."""
    parser = argparse.ArgumentParser(
        prog="token_audit",
        description="Rank Claude Code token spend from local transcripts.",
    )
    parser.add_argument(
        "--days",
        type=float,
        default=DEFAULT_DAYS,
        help=f"rolling window size in days (default {DEFAULT_DAYS})",
    )
    parser.add_argument(
        "--since",
        type=float,
        default=None,
        help="window start as a unix timestamp (overrides --days)",
    )
    parser.add_argument(
        "--until",
        type=float,
        default=None,
        help="window end as a unix timestamp (default: now)",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=TRANSCRIPT_ROOT,
        help="transcript directory to scan",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=report.REPORT_DIR,
        help="directory to write the report into",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print the machine-readable snapshot instead of the table",
    )
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="analyse without writing report files",
    )
    return parser


def _collect(root: Path, since: float, until: float) -> list[Session]:
    """Load and annotate every transcript inside the window."""
    sessions: list[Session] = []
    for path in parse.find_transcripts(root, since, until):
        session = parse.load_session(path)
        if not session.turns:
            continue
        # Re-walk the file for image cost: it needs the interleaved event order
        # that load_session flattens into separate lists.
        imagecost.annotate(session, parse.iter_events(path))
        sessions.append(session)
    return sessions


def main(argv: list[str] | None = None) -> int:
    """Run the audit and return a process exit code."""
    args = _build_parser().parse_args(argv)
    started = time.monotonic()
    until = args.until if args.until is not None else time.time()
    since = (
        args.since if args.since is not None else until - args.days * SECONDS_PER_DAY
    )

    sessions = _collect(args.root, since, until)
    if not sessions:
        sys.stderr.write(f"No transcripts with usage data under {args.root}\n")
        return EXIT_NO_DATA

    totals, axes = attribute.build(sessions)
    drift = attribute.reconcile(totals, sessions)
    window = report.Window(since=since, until=until)
    snap = report.snapshot(totals, axes, window, len(sessions))
    previous = report.load_previous(args.out)
    markdown = report.render(totals, axes, window, sessions, snap, previous)

    if not args.no_write:
        written = report.write(markdown, snap, args.out)
        sys.stderr.write(f"Wrote {written}\n")

    sys.stdout.write(json.dumps(snap, indent=2) if args.json else markdown)
    elapsed = time.monotonic() - started
    sys.stderr.write(f"Analysed {len(sessions)} sessions in {elapsed:.2f}s\n")

    if drift > MAX_DRIFT:
        sys.stderr.write(
            f"RECONCILIATION FAILED: axis rollup differs from raw usage by "
            f"{drift * 100:.2f}% (limit {MAX_DRIFT * 100:.0f}%)\n",
        )
        return EXIT_DRIFT
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
