"""The download lifecycle of a file, as typed reads and writes.

One of three query modules, split to stay under this repo's 500-line-per-file
cap: this one owns how a file got downloaded, :mod:`store_threads` owns which
threads were visited, and :mod:`store_verdicts` owns what the user decided.
Between them they hold all the SQL outside :mod:`db`, so the rest of the
package deals in dataclasses. Every function takes an already-open connection
owned by the calling thread.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

# scalar() is shared: record_files counts rows before and after. The rest are
# re-exported through __all__ so store.claim_next / store.ready_items / etc.
# keep working for downloader.py, cli.py and test_store.py unchanged.
from python_pkg.wsg_grabber._store_queries import (
    attempts_for,
    claim_next,
    claimable_values,
    counts,
    known_md5s,
    pending_downloads,
    ready_item,
    ready_items,
    scalar,
    state_of,
)
from python_pkg.wsg_grabber.states import FileState

__all__ = [
    "attempts_for",
    "claim_next",
    "claimable_values",
    "counts",
    "known_md5s",
    "local_name",
    "mark_downloaded",
    "pending_downloads",
    "ready_item",
    "ready_items",
    "record_files",
    "record_progress",
    "reset_in_flight",
    "set_state",
    "state_of",
]

if TYPE_CHECKING:
    from collections.abc import Iterable
    import sqlite3

    from python_pkg.wsg_grabber.models import (
        RemoteFile,
    )


def _now() -> str:
    """Return the current UTC time as an ISO-8601 string.

    Returns:
        str: Timestamp suitable for the index's text date columns.
    """
    return datetime.now(tz=UTC).isoformat()


def local_name(md5_b64: str, tim: int, ext: str) -> str:
    """Return the on-disk filename for a file.

    The poster-supplied name is untrusted text and is never used to build a
    path; it is carried alongside purely for display.

    Args:
        md5_b64: The API's base64 MD5, used only to disambiguate.
        tim: The CDN filename stem.
        ext: Extension including the leading dot.

    Returns:
        str: A filesystem-safe name unique per file.
    """
    suffix = md5_b64.rstrip("=")[-6:].replace("/", "_").replace("+", "-")
    return f"{tim}-{suffix}{ext}"


def record_files(conn: sqlite3.Connection, files: Iterable[RemoteFile]) -> int:
    """Insert any files not already known.

    Dedupe is structural: ``md5`` is the primary key, so a repost of identical
    bytes in another thread collapses onto the existing row and never costs a
    download.

    Args:
        conn: Open connection.
        files: Candidate attachments parsed from a thread.

    Returns:
        int: How many rows were genuinely new.
    """
    rows = [
        (
            item.md5,
            item.tim,
            item.ext,
            item.orig_name,
            item.fsize,
            item.width,
            item.height,
            item.thread_no,
            item.post_no,
            FileState.NEW.value,
            _now(),
        )
        for item in files
    ]
    if not rows:
        return 0
    before = scalar(conn, "SELECT COUNT(*) FROM files")
    conn.executemany(
        """
        INSERT INTO files (md5, tim, ext, orig_name, fsize, width, height,
                           thread_no, post_no, state, first_seen)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(md5) DO NOTHING
        """,
        rows,
    )
    return scalar(conn, "SELECT COUNT(*) FROM files") - before


def set_state(
    conn: sqlite3.Connection,
    md5_b64: str,
    state: FileState,
    *,
    error: str | None = None,
) -> None:
    """Move a file to *state*.

    Args:
        conn: Open connection.
        md5_b64: File identity.
        state: New state.
        error: Optional diagnostic kept for the next run's benefit.
    """
    conn.execute(
        "UPDATE files SET state = ?, last_error = ? WHERE md5 = ?",
        (state.value, error, md5_b64),
    )


def mark_downloaded(conn: sqlite3.Connection, md5_b64: str, name: str) -> None:
    """Record that a file finished downloading and is ready to review.

    Args:
        conn: Open connection.
        md5_b64: File identity.
        name: Filename inside the incoming directory.
    """
    conn.execute(
        """
        UPDATE files
           SET state = ?, local_name = ?, downloaded_at = ?, bytes_done = 0,
               last_error = NULL
         WHERE md5 = ?
        """,
        (FileState.READY.value, name, _now(), md5_b64),
    )


def record_progress(conn: sqlite3.Connection, md5_b64: str, done: int) -> None:
    """Persist partial download progress so a restart can resume.

    Args:
        conn: Open connection.
        md5_b64: File identity.
        done: Bytes written to the ``.part`` file so far.
    """
    conn.execute(
        "UPDATE files SET bytes_done = ? WHERE md5 = ?",
        (done, md5_b64),
    )


def reset_in_flight(conn: sqlite3.Connection) -> int:
    """Return files interrupted mid-download to the pending pool.

    A row left in ``downloading`` means the process died; the partial file on
    disk is still valid and will be resumed.

    Args:
        conn: Open connection.

    Returns:
        int: How many rows were reset.
    """
    cursor = conn.execute(
        "UPDATE files SET state = ? WHERE state = ?",
        (FileState.FAILED.value, FileState.DOWNLOADING.value),
    )
    return int(cursor.rowcount)
