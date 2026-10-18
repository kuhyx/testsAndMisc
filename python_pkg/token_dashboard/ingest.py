"""Refresh the token store: changed transcripts first, then every aux source.

Resumable by construction. Each pass walks changed files until its time budget
is spent (always at least one), commits, and exits :data:`EXIT_PENDING` if any
are left -- so a first backfill of months of transcripts is a handful of
sub-minute runs, and the systemd timer simply picks up where the last ended.

    python3 -m python_pkg.token_dashboard.ingest            # one pass
    python3 -m python_pkg.token_dashboard.ingest --budget 40
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys
import time
from typing import TYPE_CHECKING

from python_pkg.token_audit import discover, history
from python_pkg.token_dashboard import (
    ab,
    aux,
    commits,
    context_files,
    efficiency,
    finalize,
    schema,
    store,
    survival,
    walk,
)

if TYPE_CHECKING:
    import sqlite3

ROOT = Path.home() / ".claude" / "projects"
DEFAULT_BUDGET = 40.0
EXIT_PENDING = 75  # EX_TEMPFAIL: run again to continue


@dataclass(frozen=True)
class Outcome:
    """What one pass did."""

    parsed: int
    finalized: int
    complete: bool


def _changed(
    conn: sqlite3.Connection, root: Path
) -> list[tuple[Path, tuple[int, float]]]:
    """Transcripts whose size or mtime differ from what the store last saw."""
    seen = {
        path: (size, mtime)
        for path, size, mtime in conn.execute("SELECT path, size, mtime FROM files")
    }
    out = []
    for pattern in discover.PATTERNS:
        for path in root.glob(pattern):
            stat = path.stat()
            now = (stat.st_size, stat.st_mtime)
            if seen.get(str(path)) != now:
                out.append((path, now))
    # Oldest first: a backfill lands history in order, and a live session
    # (newest mtime) is re-read last, closest to the pass's end.
    return sorted(out, key=lambda item: item[1][1])


def run(
    root: Path = ROOT,
    db_path: Path = schema.DEFAULT_DB,
    report_dir: Path = history.REPORT_DIR,
    budget_s: float = DEFAULT_BUDGET,
) -> Outcome:
    """One resumable pass."""
    started = time.monotonic()
    deadline = started + budget_s
    conn = schema.connect(db_path)
    try:
        todo = _changed(conn, root)
        mains: set[str] = set()
        parsed = 0
        for path, stat in todo:
            if parsed and time.monotonic() > deadline:
                break
            facts = walk.walk_file(path, root)
            store.write(conn, facts, str(path), stat)
            mains.add(facts.parent_session or facts.key)
            parsed += 1
        for main_key in sorted(mains):
            finalize.refresh(conn, main_key)
        conn.commit()
        complete = parsed == len(todo)
        if complete:
            aux.snapshots(conn, report_dir)
            aux.lever_rows(conn, report_dir)
            aux.autopsy(conn)
            aux.activity_logs(conn, report_dir)
            commits.discover(conn)
            now = time.time()
            complete = survival.update(conn, now, deadline, time.monotonic)
            efficiency.rebuild(conn, now)
            ab.rebuild(conn)
            context_files.refresh(conn)
            context_files.price_mix(conn, now)
            conn.execute(
                "INSERT OR REPLACE INTO meta VALUES ('refreshed_at', ?)", (str(now),)
            )
            conn.commit()
    finally:
        conn.close()
    return Outcome(parsed, len(mains), complete)


def main(argv: list[str] | None = None) -> int:
    """CLI: 0 when the store is current, :data:`EXIT_PENDING` when not."""
    parser = argparse.ArgumentParser(prog="token_dashboard.ingest")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--db", type=Path, default=schema.DEFAULT_DB)
    parser.add_argument("--report-dir", type=Path, default=history.REPORT_DIR)
    parser.add_argument("--budget", type=float, default=DEFAULT_BUDGET)
    args = parser.parse_args(argv)
    started = time.monotonic()
    outcome = run(args.root, args.db, args.report_dir, args.budget)
    sys.stderr.write(
        f"token_dashboard: parsed {outcome.parsed} files, refreshed "
        f"{outcome.finalized} sessions in {time.monotonic() - started:.1f}s"
        f"{'' if outcome.complete else ' (more pending: run again)'}\n"
    )
    return 0 if outcome.complete else EXIT_PENDING


if __name__ == "__main__":
    raise SystemExit(main())
