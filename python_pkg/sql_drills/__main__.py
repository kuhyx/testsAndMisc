"""CLI: ``python3 -m python_pkg.sql_drills start|stop|list|show|check``."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from python_pkg.sql_drills import _check, _drills, _engine

_EXIT_CODES = {"pass": 0, "fail": 1, "error": 2}


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


def _dispatch(args: argparse.Namespace) -> int:
    if args.cmd == "start":
        _engine.start()
        _out(f"{_engine.CONTAINER} ready ({_engine.IMAGE})")
    elif args.cmd == "stop":
        _engine.stop()
        _out(f"{_engine.CONTAINER} removed")
    elif args.cmd == "list":
        for drill in _drills.list_drills():
            _out(f"{drill.id}  {_drills.title_of(drill)}")
    elif args.cmd == "show":
        sys.stdout.write(_drills.render_show(_drills.get_drill(args.drill)))
    else:
        result = _check.run_check(_drills.get_drill(args.drill), args.sql_file)
        _out(result.message)
        return _EXIT_CODES[result.status]
    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point; returns the process exit code."""
    args = _build_parser().parse_args(argv)
    try:
        return _dispatch(args)
    except _drills.UnknownDrillError as exc:
        _err(exc.args[0])
    except _engine.EngineError as exc:
        _err(f"error: {exc}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
