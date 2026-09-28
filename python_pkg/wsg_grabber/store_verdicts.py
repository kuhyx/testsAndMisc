"""The review trail: verdicts, and everything undo needs to reverse them.

Split out of :mod:`python_pkg.wsg_grabber.store` to stay under this repo's
500-line-per-file cap, along the seam that matters: this module owns what the
user decided, the other owns how a file got downloaded.

The trail lives in the index rather than in memory, which is what makes undo
unbounded and lets it survive quitting the reviewer.
"""

from __future__ import annotations

from datetime import UTC, datetime
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
    return datetime.now(tz=UTC).isoformat()


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


def recent_passed_names(conn: sqlite3.Connection, limit: int) -> set[str]:
    """Return the trash names of the *limit* most recent passes.

    These are the files the trash prune keeps; everything else in ``trash/``
    goes.

    Args:
        conn: Open connection.
        limit: How many passes to keep.

    Returns:
        set[str]: Filenames inside ``trash/``.
    """
    rows = conn.execute(
        """
        SELECT reviewed_name FROM files
         WHERE state = ? AND reviewed_name IS NOT NULL
         ORDER BY reviewed_at DESC, md5 DESC
         LIMIT ?
        """,
        (FileState.PASSED.value, limit),
    ).fetchall()
    return {str(row["reviewed_name"]) for row in rows}


def purge_older_passes(conn: sqlite3.Connection, limit: int) -> int:
    """Mark every pass beyond the *limit* newest as purged.

    A purged row keeps its md5, so the catalog never re-downloads the file,
    but drops out of the undo trail because its bytes are gone.

    Args:
        conn: Open connection.
        limit: How many passes stay undoable.

    Returns:
        int: Rows changed.
    """
    cursor = conn.execute(
        """
        UPDATE files
           SET state = ?, reviewed_name = NULL
         WHERE state = ?
           AND md5 NOT IN (
               SELECT md5 FROM files
                WHERE state = ? AND reviewed_name IS NOT NULL
                ORDER BY reviewed_at DESC, md5 DESC
                LIMIT ?
           )
        """,
        (FileState.PURGED.value, FileState.PASSED.value, FileState.PASSED.value, limit),
    )
    return int(cursor.rowcount)


def rename_kept(conn: sqlite3.Connection, old: str, new: str) -> None:
    """Record that a kept file changed name while being migrated.

    Args:
        conn: Open connection.
        old: Name the verdict recorded.
        new: Name the file has now.
    """
    conn.execute(
        "UPDATE files SET reviewed_name = ? WHERE state = ? AND reviewed_name = ?",
        (new, FileState.KEPT.value, old),
    )
