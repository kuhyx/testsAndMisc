"""The download lifecycle of a file, as typed reads and writes.

One of three query modules, split to stay under this repo's 500-line-per-file
cap: this one owns how a file got downloaded, :mod:`store_threads` owns which
threads were visited, and :mod:`store_verdicts` owns what the user decided.
Between them they hold all the SQL outside :mod:`db`, so the rest of the
package deals in dataclasses. Every function takes an already-open connection
owned by the calling thread.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from python_pkg.wsg_grabber.models import (
    RemoteFile,
    ReviewItem,
)
from python_pkg.wsg_grabber.states import CLAIMABLE, FileState

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence
    from pathlib import Path
    import sqlite3


def _now() -> str:
    """Return the current UTC time as an ISO-8601 string.

    Returns:
        str: Timestamp suitable for the index's text date columns.
    """
    return datetime.now(tz=timezone.utc).isoformat()


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
    before = _scalar(conn, "SELECT COUNT(*) FROM files")
    conn.executemany(
        """
        INSERT INTO files (md5, tim, ext, orig_name, fsize, width, height,
                           thread_no, post_no, state, first_seen)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(md5) DO NOTHING
        """,
        rows,
    )
    return _scalar(conn, "SELECT COUNT(*) FROM files") - before


def known_md5s(conn: sqlite3.Connection) -> set[str]:
    """Return every md5 the index has ever seen.

    Args:
        conn: Open connection.

    Returns:
        set[str]: Base64 md5 values, including terminal ones, so a reviewed or
        written-off file is never offered again.
    """
    return {str(row[0]) for row in conn.execute("SELECT md5 FROM files")}


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
    result["total"] = _scalar(conn, "SELECT COUNT(*) FROM files")
    return result


def pending_downloads(conn: sqlite3.Connection) -> int:
    """Return how many files are still waiting to be fetched.

    Args:
        conn: Open connection.

    Returns:
        int: Count of claimable rows.
    """
    return _scalar(
        conn,
        "SELECT COUNT(*) FROM files WHERE state IN (?, ?, ?)",
        claimable_values(),
    )


def _scalar(
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
