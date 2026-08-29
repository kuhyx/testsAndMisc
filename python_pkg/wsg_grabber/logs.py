r"""Structured, machine-readable event logging.

Every interesting thing this package does emits one JSON object per line, so a
session can be reconstructed afterwards without a debugger and without having
reproduced the problem live. That matters here more than usual: the parts most
likely to misbehave -- what mpv actually did with a command, whether a file was
still on disk when it was played -- sit exactly on the boundaries the test
suite has to mock, so tests cannot see them.

Reading a log back:

    jq -c 'select(.event|startswith("player."))' <logfile>
    jq -r 'select(.level=="error") | "\\(.ts) \\(.event) \\(.detail)"' <file>
    jq -r 'select(.event=="review.show") | .file' <file>   # what was shown, in order

Field names are stable. Every record carries ``ts``, ``seq``, ``level``,
``event`` and ``thread``; anything else is event-specific and always appears
under the same key.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import itertools
import json
import os
import sys
import threading
from typing import TYPE_CHECKING, Final, TextIO

from python_pkg.wsg_grabber import paths

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

LEVELS: Final[tuple[str, ...]] = ("debug", "info", "warning", "error")

_RANK: Final[dict[str, int]] = {name: index for index, name in enumerate(LEVELS)}


@dataclass
class _Session:
    """Where records go and which ones are kept."""

    sink: TextIO | None = None
    path: Path | None = None
    threshold: int = _RANK["info"]
    echo: bool = False
    lock: threading.Lock = field(default_factory=threading.Lock)
    counter: Iterator[int] = field(default_factory=lambda: itertools.count(1))


_SESSION = _Session()


def _free_path(directory: Path, stem: str) -> Path:
    """Return a log path that does not already exist.

    The stem carries a whole-second timestamp and the pid, so restarting twice
    inside one second would otherwise append a second session to the first
    one's file and make the record numbering look corrupt.

    Args:
        directory: Where logs live.
        stem: Preferred filename without its extension.

    Returns:
        Path: An unused path.
    """
    candidate = directory / f"{stem}.jsonl"
    suffix = 2
    while candidate.exists():
        candidate = directory / f"{stem}-{suffix}.jsonl"
        suffix += 1
    return candidate


def logs_dir() -> Path:
    """Return the directory holding session logs.

    Returns:
        Path: ``<data dir>/logs``.
    """
    return paths.data_dir() / "logs"


def current_path() -> Path | None:
    """Return the log file this process is writing to.

    Returns:
        Path | None: The path, or None when logging has not been started.
    """
    return _SESSION.path


def start(level: str = "info", *, echo: bool = False) -> Path:
    """Begin writing a session log and return its path.

    Args:
        level: Lowest level to record; one of :data:`LEVELS`.
        echo: Also mirror records to stderr, for watching a run live.

    Returns:
        Path: The file now being written.
    """
    stop()
    directory = logs_dir()
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%S")
    path = _free_path(directory, f"session-{stamp}-{os.getpid()}")
    with _SESSION.lock:
        _SESSION.sink = path.open("a", encoding="utf-8")
        _SESSION.path = path
        _SESSION.threshold = _RANK.get(level, _RANK["info"])
        _SESSION.echo = echo
        # Restart numbering: seq orders records within one file, so carrying it
        # over from a previous session would make the first line read as if
        # records had been lost.
        _SESSION.counter = itertools.count(1)
    event("session.start", level_wanted=level, log=str(path), pid=os.getpid())
    return path


def stop() -> None:
    """Close the session log, if one is open."""
    with _SESSION.lock:
        if _SESSION.sink is not None:
            _SESSION.sink.flush()
            _SESSION.sink.close()
        _SESSION.sink = None
        _SESSION.path = None


def event(name: str, level: str = "info", **fields: object) -> None:
    """Record one event.

    Args:
        name: Dotted event name, e.g. ``player.command``.
        level: One of :data:`LEVELS`.
        **fields: Event-specific values. Anything not JSON-encodable is
            stringified rather than dropped, so a log line is never lost to a
            serialisation error.
    """
    if _RANK.get(level, _RANK["info"]) < _SESSION.threshold:
        return
    record = {
        "ts": datetime.now(tz=UTC).isoformat(),
        "seq": next(_SESSION.counter),
        "level": level,
        "event": name,
        "thread": threading.current_thread().name,
        **fields,
    }
    line = json.dumps(record, default=str)
    with _SESSION.lock:
        if _SESSION.sink is not None:
            _SESSION.sink.write(f"{line}\n")
            _SESSION.sink.flush()
        if _SESSION.echo:
            sys.stderr.write(f"{line}\n")


def debug(name: str, **fields: object) -> None:
    """Record a debug-level event.

    Args:
        name: Dotted event name.
        **fields: Event-specific values.
    """
    event(name, level="debug", **fields)


def warning(name: str, **fields: object) -> None:
    """Record a warning-level event.

    Args:
        name: Dotted event name.
        **fields: Event-specific values.
    """
    event(name, level="warning", **fields)


def error(name: str, **fields: object) -> None:
    """Record an error-level event.

    Args:
        name: Dotted event name.
        **fields: Event-specific values.
    """
    event(name, level="error", **fields)
