"""Command-line entry point for the /wsg/ grabber.

Usage:
    PYTHONPATH=~/testsAndMisc python3 -m python_pkg.wsg_grabber
    PYTHONPATH=~/testsAndMisc python3 -m python_pkg.wsg_grabber scrape --seconds 60
    PYTHONPATH=~/testsAndMisc python3 -m python_pkg.wsg_grabber stats
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
import sys
import time
from typing import TYPE_CHECKING

from python_pkg.wsg_grabber import (
    app,
    db,
    logs,
    paths,
    player,
    store,
    store_threads,
    ui,
)
from python_pkg.wsg_grabber.states import FileState

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

_REPORT_EVERY_S = 15.0

_DESCRIPTION = (
    "Scrape 4chan /wsg/ for videos and triage them with a keep/pass reviewer. "
    "Nothing is ever deleted: a pass moves the file into the trash directory "
    "for you to clear by hand."
)


def _emit(message: str) -> None:
    """Write a line to stdout.

    Args:
        message: Line to write, without a trailing newline.
    """
    sys.stdout.write(f"{message}\n")


def build_parser() -> argparse.ArgumentParser:
    """Construct the argument parser.

    Returns:
        argparse.ArgumentParser: Parser with the ``review``, ``scrape`` and
        ``stats`` subcommands. ``review`` is the default.
    """
    parser = argparse.ArgumentParser(
        prog="python -m python_pkg.wsg_grabber",
        description=_DESCRIPTION,
    )
    parser.add_argument(
        "--log-level",
        choices=logs.LEVELS,
        default="info",
        help="detail written to the session log (default: info)",
    )
    parser.add_argument(
        "--echo-log",
        action="store_true",
        help="also print log records to stderr as they happen",
    )
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser(
        "review",
        help="download in the background and review on screen (default)",
    )
    subparsers.add_parser("stats", help="print index counts and exit")
    subparsers.add_parser(
        "logs",
        help="show where session logs live and summarise the newest one",
    )
    scrape_parser = subparsers.add_parser(
        "scrape",
        help="index and download without opening the reviewer",
    )
    scrape_parser.add_argument(
        "--seconds",
        type=float,
        default=0.0,
        help="stop after this long (0 means run until interrupted)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the requested subcommand.

    Args:
        argv: Argument list, defaulting to ``sys.argv[1:]``.

    Returns:
        int: Process exit status.
    """
    args = build_parser().parse_args(argv)
    logs.start(args.log_level, echo=args.echo_log)
    try:
        return _dispatch(args)
    finally:
        logs.stop()


def _dispatch(args: argparse.Namespace) -> int:
    """Run the subcommand named in *args*.

    Args:
        args: Parsed arguments.

    Returns:
        int: Process exit status.
    """
    if args.command == "logs":
        return show_logs()
    if args.command == "stats":
        return stats()
    if args.command == "scrape":
        return scrape(args.seconds)
    return open_reviewer()


def stats() -> int:
    """Print what the index knows.

    Returns:
        int: Exit status.
    """
    paths.ensure_dirs()
    conn = db.open_index(paths.db_path())
    try:
        counts = store.counts(conn)
        _emit(f"index        {paths.db_path()}")
        _emit(f"known files  {counts.get('total', 0)}")
        for state in FileState:
            _emit(f"  {state.value:<12} {counts.get(state.value, 0)}")
        _emit(f"threads      {len(store_threads.known_threads(conn))}")
        _emit(f"keep dir     {paths.keep_dir()}")
        _emit(f"trash dir    {paths.trash_dir()}  (never emptied automatically)")
    finally:
        conn.close()
    return 0


def scrape(seconds: float, sleeper: Callable[[float], None] | None = None) -> int:
    """Index and download without opening a window.

    Args:
        seconds: Stop after this long; 0 runs until interrupted.
        sleeper: Optional stand-in for :func:`time.sleep`, used by tests to
            avoid actually waiting.

    Returns:
        int: Exit status.
    """
    rest = time.sleep if sleeper is None else sleeper
    session = app.open_session()
    started = time.monotonic()
    reported = started
    try:
        _emit("scraping /wsg/ — Ctrl-C to stop")
        while True:
            rest(1.0)
            now = time.monotonic()
            if now - reported >= _REPORT_EVERY_S:
                reported = now
                _emit(progress(session))
            if seconds and now - started >= seconds:
                break
    except KeyboardInterrupt:
        _emit("stopping")
    finally:
        _emit(progress(session))
        session.shutdown()
    return 0


def progress(session: app.Session) -> str:
    """Summarise index progress.

    Args:
        session: The running session.

    Returns:
        str: One-line summary.
    """
    counts = store.counts(session.conn)
    return (
        f"known {counts.get('total', 0)} · "
        f"ready {counts.get(FileState.READY.value, 0)} · "
        f"pending {store.pending_downloads(session.conn)}"
    )


def open_reviewer() -> int:
    """Open the reviewer window and hand control to it.

    Returns:
        int: Exit status.
    """
    session = app.open_session()
    try:
        window = ui.ReviewWindow(
            app.initial_state(session),
            session.events,
            ui.Callbacks(
                commit=session.commit,
                missing=session.missing,
                undo=session.undo,
                shutdown=session.shutdown,
            ),
        )
        window.attach_player(
            player.MpvPlayer(window.video_wid(), paths.ipc_socket_path()),
        )
        window.run()
    except BaseException:
        # The worker is a non-daemon thread, so anything raised between opening
        # the session and entering the Tk loop -- mpv missing, a stale socket --
        # would otherwise leave the process alive forever with no window.
        logs.error("review.startup_failed")
        session.shutdown()
        raise
    return 0


def show_logs() -> int:
    """Print where logs live and summarise the most recent session.

    Returns:
        int: Exit status.
    """
    directory = logs.logs_dir()
    _emit(f"log directory  {directory}")
    sessions = sorted(directory.glob("session-*.jsonl"))
    if not sessions:
        _emit("no session logs yet")
        return 0
    newest = sessions[-1]
    _emit(f"newest session {newest}")
    _emit(f"sessions kept  {len(sessions)}")
    _emit("")
    _emit(summarise(newest))
    _emit("")
    _emit("Useful queries:")
    _emit(f"  jq -c 'select(.level==\"error\")' {newest}")
    _emit(f"  jq -r 'select(.event==\"review.show\")|.file' {newest}")
    _emit(f"  jq -c 'select(.event|startswith(\"player.\"))' {newest}")
    return 0


def summarise(path: Path) -> str:
    """Count events by name and level in one session log.

    Args:
        path: A session JSONL file.

    Returns:
        str: A short human-readable tally.
    """
    by_event: Counter[str] = Counter()
    by_level: Counter[str] = Counter()
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            record = json.loads(line)
        except ValueError:
            continue
        by_event[str(record.get("event"))] += 1
        by_level[str(record.get("level"))] += 1
    levels = "  ".join(f"{name}={count}" for name, count in sorted(by_level.items()))
    lines = [f"records by level: {levels or 'none'}", "events:"]
    lines.extend(f"  {name:<24} {count}" for name, count in by_event.most_common(15))
    return "\n".join(lines)
