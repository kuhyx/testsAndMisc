"""Bookkeeping for the ``threads`` table.

Split out of :mod:`python_pkg.wsg_grabber.store` to stay under this repo's
500-line-per-file cap. The seam is the natural one: this module owns which
threads have been visited and what their last ``Last-Modified`` was, which is
what lets an unchanged thread cost a 304 rather than a re-parse.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import sqlite3

    from python_pkg.wsg_grabber.models import ThreadRef


def _now() -> str:
    """Return the current UTC time as an ISO-8601 string.

    Returns:
        str: Timestamp suitable for the index's text date columns.
    """
    return datetime.now(tz=UTC).isoformat()


def known_threads(conn: sqlite3.Connection) -> dict[int, int]:
    """Return each known thread's last-modified stamp.

    Args:
        conn: Open connection.

    Returns:
        dict[int, int]: Thread number mapped to its stored API timestamp.
    """
    return {
        int(row["thread_no"]): int(row["api_last_mod"])
        for row in conn.execute("SELECT thread_no, api_last_mod FROM threads")
    }


def http_last_modified(conn: sqlite3.Connection, thread_no: int) -> str | None:
    """Return the stored ``Last-Modified`` header for a thread.

    Args:
        conn: Open connection.
        thread_no: Thread identifier.

    Returns:
        str | None: Header value to send back as ``If-Modified-Since``.
    """
    row = conn.execute(
        "SELECT http_last_mod FROM threads WHERE thread_no = ?",
        (thread_no,),
    ).fetchone()
    if row is None or row["http_last_mod"] is None:
        return None
    return str(row["http_last_mod"])


def record_thread(
    conn: sqlite3.Connection,
    ref: ThreadRef,
    header: str | None,
    status: str = "live",
) -> None:
    """Insert or update a thread's bookkeeping row.

    Args:
        conn: Open connection.
        ref: Thread number and its API timestamp.
        header: ``Last-Modified`` header from the thread fetch, if any.
        status: ``live`` or ``gone``.
    """
    conn.execute(
        """
        INSERT INTO threads (thread_no, api_last_mod, http_last_mod,
                             last_checked, status)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(thread_no) DO UPDATE SET
            api_last_mod  = excluded.api_last_mod,
            http_last_mod = COALESCE(excluded.http_last_mod, threads.http_last_mod),
            last_checked  = excluded.last_checked,
            status        = excluded.status
        """,
        (ref.thread_no, ref.api_last_modified, header, _now(), status),
    )


def mark_thread_gone(conn: sqlite3.Connection, thread_no: int) -> None:
    """Flag a thread as no longer fetchable.

    This inserts rather than merely updating: a thread can 404 the very first
    time it is seen, and a plain UPDATE would touch no rows, leaving nothing to
    record that it is dead. It would then be re-fetched on every future run.

    Args:
        conn: Open connection.
        thread_no: Thread identifier.
    """
    conn.execute(
        """
        INSERT INTO threads (thread_no, api_last_mod, http_last_mod,
                             last_checked, status)
        VALUES (?, 0, NULL, ?, 'gone')
        ON CONFLICT(thread_no) DO UPDATE SET
            status       = 'gone',
            last_checked = excluded.last_checked
        """,
        (thread_no, _now()),
    )


def cached_last_modified(conn: sqlite3.Connection, url: str) -> str | None:
    """Return the stored ``Last-Modified`` for a board-level endpoint.

    ``threads.json`` and ``archive.json`` are not tied to any one thread, so
    their stamps live here rather than in the threads table. Without this the
    reviewer re-fetches both unconditionally on every idle cycle, forever.

    Args:
        conn: Open connection.
        url: Absolute API URL.

    Returns:
        str | None: Header value to send back as ``If-Modified-Since``.
    """
    row = conn.execute(
        "SELECT last_modified FROM http_cache WHERE url = ?",
        (url,),
    ).fetchone()
    return None if row is None else str(row["last_modified"])


def record_last_modified(
    conn: sqlite3.Connection,
    url: str,
    stamp: str | None,
) -> None:
    """Store the ``Last-Modified`` a board-level endpoint returned.

    Args:
        conn: Open connection.
        url: Absolute API URL.
        stamp: Header value; ignored when the server did not send one.
    """
    if stamp is None:
        return
    conn.execute(
        """
        INSERT INTO http_cache (url, last_modified) VALUES (?, ?)
        ON CONFLICT(url) DO UPDATE SET last_modified = excluded.last_modified
        """,
        (url, stamp),
    )
