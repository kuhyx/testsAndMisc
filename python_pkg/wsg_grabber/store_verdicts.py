"""The review trail: verdicts, and everything undo needs to reverse them.

Split out of :mod:`python_pkg.wsg_grabber.store` to stay under this repo's
500-line-per-file cap, along the seam that matters: this module owns what the
user decided, the other owns how a file got downloaded.

The trail lives in the index rather than in memory, which is what makes undo
unbounded and lets it survive quitting the reviewer.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from python_pkg.wsg_grabber.models import ReviewedItem, ReviewItem, Verdict
from python_pkg.wsg_grabber.states import FileState

if TYPE_CHECKING:
    from pathlib import Path
    import sqlite3


def _now() -> str:
    """Return the current UTC time as an ISO-8601 string.

    Returns:
        str: Timestamp suitable for the index's text date columns.
    """
    return datetime.now(tz=timezone.utc).isoformat()


def _scalar(conn: sqlite3.Connection, sql: str, params: list[str]) -> int:
    """Run a single-value query and return it as an int.

    Args:
        conn: Open connection.
        sql: Query yielding exactly one column.
        params: Bound parameters.

    Returns:
        int: The first column of the first row.
    """
    return int(conn.execute(sql, params).fetchone()[0])


def record_verdict(
    conn: sqlite3.Connection,
    md5_b64: str,
    state: FileState,
    reviewed_name: str | None = None,
) -> None:
    """Store the user's decision about a file.

    Args:
        conn: Open connection.
        md5_b64: File identity.
        state: Either ``KEPT`` or ``PASSED``.
        reviewed_name: Name the file now has in keep/ or trash/. Persisting it
            is what lets the verdict be undone in a later session.
    """
    conn.execute(
        """
        UPDATE files
           SET state = ?, reviewed_at = ?, reviewed_name = ?
         WHERE md5 = ?
        """,
        (state.value, _now(), reviewed_name, md5_b64),
    )


def reviewed_count(conn: sqlite3.Connection) -> int:
    """Return how many verdicts could still be taken back.

    Args:
        conn: Open connection.

    Returns:
        int: Count of reviewed files whose destination name is known.
    """
    return _scalar(
        conn,
        """
        SELECT COUNT(*) FROM files
         WHERE state IN (?, ?) AND reviewed_name IS NOT NULL
        """,
        [FileState.KEPT.value, FileState.PASSED.value],
    )


def newest_verdict(
    conn: sqlite3.Connection,
    directory: Path,
) -> ReviewedItem | None:
    """Return the most recent verdict that can be undone.

    Reading this from the index rather than from memory is what makes undo
    survive quitting, and unbounded: every verdict ever recorded is a candidate,
    newest first.

    Args:
        conn: Open connection.
        directory: Where an undone file should be put back.

    Returns:
        ReviewedItem | None: The verdict to reverse, or None when there is none.
    """
    row = conn.execute(
        """
        SELECT md5, local_name, reviewed_name, orig_name, ext, fsize,
               width, height, state
          FROM files
         WHERE state IN (?, ?) AND reviewed_name IS NOT NULL
         ORDER BY reviewed_at DESC, md5 DESC
         LIMIT 1
        """,
        (FileState.KEPT.value, FileState.PASSED.value),
    ).fetchone()
    if row is None:
        return None
    return ReviewedItem(
        item=ReviewItem(
            md5=row["md5"],
            path=directory / row["local_name"],
            orig_name=f"{row['orig_name']}{row['ext']}",
            fsize=row["fsize"],
            width=row["width"],
            height=row["height"],
        ),
        choice=Verdict.KEEP if row["state"] == FileState.KEPT.value else Verdict.SKIP,
        reviewed_name=row["reviewed_name"],
    )


def forget_verdict(conn: sqlite3.Connection, md5_b64: str) -> None:
    """Make a verdict un-undoable without changing it.

    Used when the file is no longer where the verdict left it, so the same
    entry does not keep surfacing as the next thing to undo.

    Args:
        conn: Open connection.
        md5_b64: File identity.
    """
    conn.execute(
        "UPDATE files SET reviewed_name = NULL WHERE md5 = ?",
        (md5_b64,),
    )


def restore_for_review(conn: sqlite3.Connection, md5_b64: str, name: str) -> None:
    """Undo a verdict, returning the file to the review queue.

    Args:
        conn: Open connection.
        md5_b64: File identity.
        name: Filename it has again inside the incoming directory.
    """
    conn.execute(
        """
        UPDATE files
           SET state = ?, local_name = ?, reviewed_at = NULL,
               reviewed_name = NULL
         WHERE md5 = ?
        """,
        (FileState.READY.value, name, md5_b64),
    )
