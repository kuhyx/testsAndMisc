"""Schema definition, connection setup and migration for the file index.

sqlite rather than the JSON state files used elsewhere in this repo: two threads
write concurrently (the downloader appending rows, the UI recording verdicts),
the seen-set grows without bound, and "have I seen this md5" must stay O(1).
Rewriting a whole JSON document per verdict would not survive either property.

``check_same_thread`` is deliberately left at its default so a connection that
escapes its owning thread raises loudly instead of corrupting the file.
"""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING, Final

from python_pkg.wsg_grabber.constants import (
    DB_BUSY_TIMEOUT_MS,
    DB_TIMEOUT_S,
    SCHEMA_VERSION,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

_SCHEMA: Final[tuple[str, ...]] = (
    """
    CREATE TABLE IF NOT EXISTS files (
        md5           TEXT    PRIMARY KEY,
        tim           INTEGER NOT NULL,
        ext           TEXT    NOT NULL,
        orig_name     TEXT    NOT NULL,
        fsize         INTEGER NOT NULL,
        width         INTEGER NOT NULL,
        height        INTEGER NOT NULL,
        thread_no     INTEGER NOT NULL,
        post_no       INTEGER NOT NULL,
        state         TEXT    NOT NULL,
        attempts      INTEGER NOT NULL DEFAULT 0,
        bytes_done    INTEGER NOT NULL DEFAULT 0,
        last_error    TEXT,
        local_name    TEXT,
        first_seen    TEXT    NOT NULL,
        downloaded_at TEXT,
        reviewed_at   TEXT,
        reviewed_name TEXT
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_files_state ON files(state)",
    "CREATE INDEX IF NOT EXISTS idx_files_claim ON files(state, first_seen)",
    """
    CREATE TABLE IF NOT EXISTS threads (
        thread_no     INTEGER PRIMARY KEY,
        api_last_mod  INTEGER NOT NULL,
        http_last_mod TEXT,
        last_checked  TEXT    NOT NULL,
        status        TEXT    NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_threads_status ON threads(status)",
    "CREATE INDEX IF NOT EXISTS idx_files_reviewed ON files(reviewed_at)",
    """
    CREATE TABLE IF NOT EXISTS http_cache (
        url           TEXT PRIMARY KEY,
        last_modified TEXT NOT NULL
    )
    """,
)


class SchemaTooNewError(RuntimeError):
    """Raised when the index was written by a newer version of this tool."""


def connect(path: Path) -> sqlite3.Connection:
    """Open *path* with the pragmas this package relies on.

    WAL is what lets the downloader thread write while the UI thread reads and
    writes verdicts, without either blocking the other.

    Args:
        path: Location of the sqlite file; its parent must already exist.

    Returns:
        sqlite3.Connection: Autocommit connection with row access by name.
    """
    conn = sqlite3.connect(path, timeout=DB_TIMEOUT_S, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute(f"PRAGMA busy_timeout={DB_BUSY_TIMEOUT_MS}")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def ensure_schema(conn: sqlite3.Connection) -> int:
    """Create or migrate the schema, returning the version now in force.

    Args:
        conn: Open connection.

    Returns:
        int: The schema version after this call.

    Raises:
        SchemaTooNewError: If the file was written by a newer release, in which
            case silently downgrading it would lose data.
    """
    version = int(conn.execute("PRAGMA user_version").fetchone()[0])
    if version > SCHEMA_VERSION:
        msg = (
            f"index schema is version {version} but this build understands "
            f"at most {SCHEMA_VERSION}; upgrade the tool instead of "
            f"downgrading the index"
        )
        raise SchemaTooNewError(msg)
    if version == SCHEMA_VERSION:
        return version
    for statement in _SCHEMA:
        conn.execute(statement)
    # A fresh database already has the current shape from _SCHEMA, so most
    # steps have no migration. Each one that does is idempotent, which keeps
    # this safe either way.
    for step in range(version, SCHEMA_VERSION):
        migrate = _MIGRATIONS.get(step)
        if migrate is not None:
            migrate(conn)
    conn.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
    return SCHEMA_VERSION


def _to_v2(conn: sqlite3.Connection) -> None:
    """Add the column that makes a verdict reversible after a restart.

    Undo needs to know the name the file was given in keep/ or trash/, which
    may differ from its name in incoming/ when a collision forced a rename.

    Args:
        conn: Open connection.
    """
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(files)")}
    if "reviewed_name" not in columns:
        conn.execute("ALTER TABLE files ADD COLUMN reviewed_name TEXT")


# Keyed by the version being upgraded FROM.
_MIGRATIONS: Final[dict[int, Callable[[sqlite3.Connection], None]]] = {
    1: _to_v2,
}


def open_index(path: Path) -> sqlite3.Connection:
    """Open *path* and bring its schema up to date.

    Args:
        path: Location of the sqlite file.

    Returns:
        sqlite3.Connection: Ready-to-use connection.
    """
    conn = connect(path)
    ensure_schema(conn)
    return conn
