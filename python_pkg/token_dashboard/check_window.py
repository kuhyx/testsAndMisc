"""Reconcile the store against a token_audit snapshot: within 1% or exit 1.

The snapshot's ``usd_per_day`` is ``usd_total`` over the span between the
earliest and latest priced record inside its window (not the window length),
so the same definition is applied to the store's turns here.

    python3 -m python_pkg.token_dashboard.check_window            # newest
    python3 -m python_pkg.token_dashboard.check_window --snapshot 2026-10-17
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import TYPE_CHECKING

from python_pkg.token_audit import history
from python_pkg.token_dashboard import schema

if TYPE_CHECKING:
    import sqlite3

TOLERANCE = 0.01
DAY_S = 86400.0
MIN_SPAN_S = 60.0


def measure(conn: sqlite3.Connection, since: float, until: float) -> dict[str, float]:
    """``usd_total``, ``usd_per_day`` and ``calls`` from the store's turns."""
    usd, calls, first, last = conn.execute(
        "SELECT SUM(usd), COUNT(*), MIN(ts), MAX(ts) FROM turns"
        " WHERE ts BETWEEN ? AND ?",
        (since, until),
    ).fetchone()
    usd = usd or 0.0
    days = max((last or 0) - (first or 0), MIN_SPAN_S) / DAY_S
    return {"usd_total": usd, "usd_per_day": usd / days, "calls": float(calls)}


def main(argv: list[str] | None = None) -> int:
    """Compare and print one line per metric; 0 when every one is within 1%."""
    parser = argparse.ArgumentParser(prog="token_dashboard.check_window")
    parser.add_argument("--db", type=Path, default=schema.DEFAULT_DB)
    parser.add_argument("--report-dir", type=Path, default=history.REPORT_DIR)
    parser.add_argument("--snapshot", default=None, help="history file stem")
    args = parser.parse_args(argv)
    folder = args.report_dir / history.HISTORY_NAME
    path = (
        folder / f"{args.snapshot}.json"
        if args.snapshot
        else max(folder.glob("*.json"), default=None)
    )
    if path is None or not path.is_file() or not args.db.is_file():
        sys.stderr.write(f"missing snapshot or store ({path}, {args.db})\n")
        return 1
    snap = json.loads(path.read_text(encoding="utf-8"))
    window = snap["window"]
    conn = schema.connect(args.db, readonly=True)
    try:
        got = measure(conn, float(window["since"]), float(window["until"]))
    finally:
        conn.close()
    ok = True
    for key, value in got.items():
        want = float(snap["metrics"][key])
        drift = abs(value - want) / want if want else 0.0
        ok &= drift <= TOLERANCE
        sys.stdout.write(
            f"{key}: store {value:,.2f} vs snapshot {want:,.2f}"
            f" ({drift:.2%}) {'OK' if drift <= TOLERANCE else 'FAIL'}\n"
        )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
