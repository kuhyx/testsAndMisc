"""The ``logs`` subcommand: where session logs live and what is in the newest.

Split out of :mod:`python_pkg.wsg_grabber.cli` to keep that module under the
250-line cap. This is read-only reporting over the JSONL session logs and
shares nothing with the scrape/review flow beyond the log directory itself.
"""

from __future__ import annotations

from collections import Counter
import json
import sys
from typing import TYPE_CHECKING

from python_pkg.wsg_grabber import logs

if TYPE_CHECKING:
    from pathlib import Path


def _emit(message: str) -> None:
    """Write a line to stdout.

    Args:
        message: Line to write, without a trailing newline.
    """
    sys.stdout.write(f"{message}\n")


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
