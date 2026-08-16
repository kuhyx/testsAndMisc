"""Read-only projections over the file index, plus the atomic claim.

Split out of :mod:`python_pkg.wsg_grabber.store` to keep it under the 250-line
cap. ``store`` owns the writes that move a file through its lifecycle; this
module asks the questions -- what is reviewable, how many of each state there
are, how much work is left -- and owns ``claim_next``, which is the one write
that has to be a single atomic transaction against those same reads.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from python_pkg.wsg_grabber.models import RemoteFile, ReviewItem
from python_pkg.wsg_grabber.states import CLAIMABLE, FileState

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path
    import sqlite3


def scalar(
    conn: sqlite3.Connection,
    sql: str,
    params: Sequence[object] | Mapping[str, object] | None = None,
) -> int:
    """Run a single-value query and return it as an int.

    Args:
        conn: Open connection.
        sql: Query yielding exactly one column.
        params: Optional bound parameters.

    Returns:
        int: The first column of the first row.
    """
    cursor = conn.execute(sql) if params is None else conn.execute(sql, params)
    return int(cursor.fetchone()[0])


def claimable_values() -> list[str]:
    """Return the state values a download worker may pick up, in a stable order.

    The queries below spell out one placeholder per member rather than building
    the ``IN`` list at runtime, so the SQL stays a literal. ``test_store``
    pins the member count so adding a state cannot silently desync the two.

    Returns:
        list[str]: Sorted state values.
    """
    return [state.value for state in sorted(CLAIMABLE)]


def claim_next(conn: sqlite3.Connection) -> RemoteFile | None:
    """Atomically take the oldest downloadable file and mark it in flight.

    Args:
        conn: Open connection.

    Returns:
        RemoteFile | None: The claimed file, or None when nothing is pending.
    """
    conn.execute("BEGIN IMMEDIATE")
    try:
        row = conn.execute(
            """
            SELECT md5, tim, ext, orig_name, fsize, width, height,
                   thread_no, post_no
              FROM files
             WHERE state IN (?, ?, ?)
             ORDER BY first_seen, md5
             LIMIT 1
            """,
            claimable_values(),
        ).fetchone()
        if row is None:
            conn.execute("COMMIT")
            return None
        conn.execute(
            "UPDATE files SET state = ?, attempts = attempts + 1 WHERE md5 = ?",
            (FileState.DOWNLOADING.value, row["md5"]),
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return RemoteFile(
        md5=row["md5"],
        tim=row["tim"],
        ext=row["ext"],
        orig_name=row["orig_name"],
        fsize=row["fsize"],
        width=row["width"],
        height=row["height"],
        thread_no=row["thread_no"],
        post_no=row["post_no"],
    )


def ready_items(conn: sqlite3.Connection, directory: Path) -> list[ReviewItem]:
    """Return downloaded files still awaiting a verdict, oldest first.

    Args:
        conn: Open connection.
        directory: Where downloaded files live.

    Returns:
        list[ReviewItem]: Reviewable videos.
    """
    rows = conn.execute(
        """
        SELECT md5, local_name, orig_name, ext, fsize, width, height
          FROM files
         WHERE state = ? AND local_name IS NOT NULL
         ORDER BY downloaded_at, md5
        """,
        (FileState.READY.value,),
    ).fetchall()
    return [
        ReviewItem(
            md5=row["md5"],
            path=directory / row["local_name"],
            orig_name=f"{row['orig_name']}{row['ext']}",
            fsize=row["fsize"],
            width=row["width"],
            height=row["height"],
        )
        for row in rows
    ]


def ready_item(source: RemoteFile, path: Path) -> ReviewItem:
    """Build the reviewer's view of a file that just finished downloading.

    Args:
        source: The catalogue record it came from.
        path: Where the verified bytes now live.

    Returns:
        ReviewItem: Value handed to the UI thread.
    """
    return ReviewItem(
        md5=source.md5,
        path=path,
        orig_name=f"{source.orig_name}{source.ext}",
        fsize=source.fsize,
        width=source.width,
        height=source.height,
    )


def counts(conn: sqlite3.Connection) -> dict[str, int]:
    """Return the number of files in each state.

    Args:
        conn: Open connection.

    Returns:
        dict[str, int]: State value mapped to row count, plus ``total``.
    """
    result = {
        str(row["state"]): int(row["n"])
        for row in conn.execute(
            "SELECT state, COUNT(*) AS n FROM files GROUP BY state",
        )
    }
    result["total"] = scalar(conn, "SELECT COUNT(*) FROM files")
    return result


def pending_downloads(conn: sqlite3.Connection) -> int:
    """Return how many files are still waiting to be fetched.

    Args:
        conn: Open connection.

    Returns:
        int: Count of claimable rows.
    """
    return scalar(
        conn,
        "SELECT COUNT(*) FROM files WHERE state IN (?, ?, ?)",
        claimable_values(),
    )


def known_md5s(conn: sqlite3.Connection) -> set[str]:
    """Return every md5 the index has ever seen.

    Args:
        conn: Open connection.

    Returns:
        set[str]: Base64 md5 values, including terminal ones, so a reviewed or
        written-off file is never offered again.
    """
    return {str(row[0]) for row in conn.execute("SELECT md5 FROM files")}


def state_of(conn: sqlite3.Connection, md5_b64: str) -> FileState | None:
    """Return a file's current state.

    Args:
        conn: Open connection.
        md5_b64: File identity.

    Returns:
        FileState | None: The state, or None when the file is unknown.
    """
    row = conn.execute(
        "SELECT state FROM files WHERE md5 = ?",
        (md5_b64,),
    ).fetchone()
    return None if row is None else FileState(row["state"])


def attempts_for(conn: sqlite3.Connection, md5_b64: str) -> int:
    """Return how many download attempts a file has had.

    Args:
        conn: Open connection.
        md5_b64: File identity.

    Returns:
        int: Attempt count, zero when the file is unknown.
    """
    row = conn.execute(
        "SELECT attempts FROM files WHERE md5 = ?",
        (md5_b64,),
    ).fetchone()
    return 0 if row is None else int(row["attempts"])
