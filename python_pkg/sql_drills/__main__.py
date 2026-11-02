"""CLI: ``python3 -m python_pkg.sql_drills start|stop|list|show|check``.

A thin wrapper over the shared ``sql_drills`` package (kuhyx/utils).
"""

from __future__ import annotations

import argparse
import importlib
import logging
from pathlib import Path
import sys

import sql_drills as sd

_LOG = logging.getLogger(__name__)


def _heartbeat() -> None:
    """Tell the optional focus tracker that practice is happening.

    Soft dependency: absent module -> silent no-op; a tracker error is logged
    and never changes the drill's result or exit code.
    """
    try:
        tracker = importlib.import_module("focus_project")
    except ImportError:
        return
    try:
        tracker.record_activity("sql_drills", "heartbeat")
    except OSError, ValueError:
        _LOG.exception("focus tracker heartbeat failed")


def _out(line: str) -> None:
    sys.stdout.write(f"{line}\n")


def _err(line: str) -> None:
    sys.stderr.write(f"{line}\n")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sql_drills", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("start", help="start the MySQL 8.0.33 container and wait")
    sub.add_parser("stop", help="remove the container")
    sub.add_parser("list", help="list drills in priority order")
    show = sub.add_parser("show", help="print task, schema, expected sample")
    show.add_argument("drill", help="drill id or number, e.g. 03")
    check = sub.add_parser("check", help="grade a .sql file against a drill")
    check.add_argument("drill", help="drill id or number, e.g. 03")
    check.add_argument("sql_file", type=Path)
    return parser


def _render_show(drill: sd.Drill) -> str:
    tail = "## Query to predict" if drill.query else "## Expected output (sample)"
    body = drill.query or "\n".join("\t".join(r) for r in drill.expected_preview)
    return (
        f"{drill.task_md.strip()}\n\n## Schema\n\n{drill.schema_sql.strip()}\n\n"
        f"{tail}\n\n{body}\n"
    )


def _check(drill_id: str, sql_file: Path) -> int:
    if not sql_file.is_file():
        _out(f"query file not found: {sql_file}")
        return 2
    res = sd.run(drill_id, sql_file.read_text())
    if res.error is not None and not res.match:
        _out(f"SQL error: {res.error}")
        return 2
    if res.match:
        _out(f"PASS {drill_id} ({len(res.rows)} rows)")
        return 0
    _out(
        f"FAIL {drill_id}: expected {len(res.expected_rows)} rows, got {len(res.rows)}"
    )
    for row, col, want, got in res.cell_diff:
        _out(f"line {row + 1} cell {col + 1}: expected {want!r}, actual {got!r}")
    return 1


def _dispatch(args: argparse.Namespace) -> int:
    if args.cmd == "start":
        sd.ensure_running()
        _out(f"{sd.CONTAINER} ready ({sd.IMAGE})")
    elif args.cmd == "stop":
        sd.stop()
        _out(f"{sd.CONTAINER} removed")
    elif args.cmd == "list":
        for meta in sd.list_drills():
            _out(f"{meta.id}  {meta.title}")
    elif args.cmd == "show":
        _heartbeat()
        sys.stdout.write(_render_show(sd.get_drill(args.drill)))
    else:
        _heartbeat()
        return _check(args.drill, args.sql_file)
    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point; returns the process exit code."""
    args = _build_parser().parse_args(argv)
    try:
        return _dispatch(args)
    except sd.UnknownDrillError as exc:
        _err(exc.args[0])
    except sd.EngineError as exc:
        _err(f"error: {exc}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
