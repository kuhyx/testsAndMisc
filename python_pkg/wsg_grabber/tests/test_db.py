"""Tests for connection setup and schema migration."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from python_pkg.wsg_grabber import db, paths
from python_pkg.wsg_grabber.constants import SCHEMA_VERSION

if TYPE_CHECKING:
    from pathlib import Path
    import sqlite3


def _fresh(tmp_path: Path) -> sqlite3.Connection:
    """Open a brand new index inside the sandbox.

    Args:
        tmp_path: Per-test temporary directory.

    Returns:
        sqlite3.Connection: Migrated connection.
    """
    return db.open_index(tmp_path / "index.db")


def test_connect_enables_wal_and_row_access(tmp_path: Path) -> None:
    conn = db.connect(tmp_path / "index.db")
    try:
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert str(mode).lower() == "wal"
        conn.execute("CREATE TABLE t (a INTEGER)")
        conn.execute("INSERT INTO t VALUES (1)")
        assert conn.execute("SELECT a FROM t").fetchone()["a"] == 1
    finally:
        conn.close()


def test_ensure_schema_creates_tables_and_stamps_the_version(tmp_path: Path) -> None:
    conn = db.connect(tmp_path / "index.db")
    try:
        assert db.ensure_schema(conn) == SCHEMA_VERSION
        names = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        assert {"files", "threads"} <= names
        assert int(conn.execute("PRAGMA user_version").fetchone()[0]) == SCHEMA_VERSION
    finally:
        conn.close()


def test_ensure_schema_is_idempotent(tmp_path: Path) -> None:
    conn = db.connect(tmp_path / "index.db")
    try:
        db.ensure_schema(conn)
        assert db.ensure_schema(conn) == SCHEMA_VERSION
    finally:
        conn.close()


def test_a_newer_schema_is_refused_rather_than_downgraded(tmp_path: Path) -> None:
    conn = db.connect(tmp_path / "index.db")
    try:
        conn.execute(f"PRAGMA user_version={SCHEMA_VERSION + 1}")
        with pytest.raises(db.SchemaTooNewError, match="upgrade the tool"):
            db.ensure_schema(conn)
    finally:
        conn.close()


def test_open_index_returns_a_migrated_connection(tmp_path: Path) -> None:
    conn = _fresh(tmp_path)
    try:
        assert conn.execute("SELECT COUNT(*) FROM files").fetchone()[0] == 0
    finally:
        conn.close()


def test_index_lands_inside_the_sandbox(tmp_path: Path) -> None:
    paths.ensure_dirs()
    conn = db.open_index(paths.db_path())
    try:
        assert str(paths.db_path()).startswith(str(tmp_path))
        assert paths.db_path().exists()
    finally:
        conn.close()


def test_a_version_1_index_is_migrated_in_place(tmp_path: Path) -> None:
    """An index written before undo existed must keep its rows and gain the column."""
    path = tmp_path / "old.db"
    conn = db.connect(path)
    try:
        conn.execute(
            """
            CREATE TABLE files (
                md5 TEXT PRIMARY KEY, tim INTEGER NOT NULL, ext TEXT NOT NULL,
                orig_name TEXT NOT NULL, fsize INTEGER NOT NULL,
                width INTEGER NOT NULL, height INTEGER NOT NULL,
                thread_no INTEGER NOT NULL, post_no INTEGER NOT NULL,
                state TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
                bytes_done INTEGER NOT NULL DEFAULT 0, last_error TEXT,
                local_name TEXT, first_seen TEXT NOT NULL,
                downloaded_at TEXT, reviewed_at TEXT
            )
            """,
        )
        conn.execute(
            "INSERT INTO files (md5,tim,ext,orig_name,fsize,width,height,"
            "thread_no,post_no,state,first_seen) "
            "VALUES ('OLD',1,'.webm','x',1,1,1,1,1,'kept','then')",
        )
        conn.execute("PRAGMA user_version=1")
    finally:
        conn.close()

    conn = db.open_index(path)
    try:
        assert int(conn.execute("PRAGMA user_version").fetchone()[0]) == SCHEMA_VERSION
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(files)")}
        assert "reviewed_name" in columns
        # the existing row survives, simply without an undo trail
        row = conn.execute("SELECT state, reviewed_name FROM files").fetchone()
        assert row["state"] == "kept"
        assert row["reviewed_name"] is None
    finally:
        conn.close()
