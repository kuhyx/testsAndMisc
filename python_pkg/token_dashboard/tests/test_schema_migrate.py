from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

import pytest

from python_pkg.token_dashboard import schema

if TYPE_CHECKING:
    from pathlib import Path


def _v1_store(path: Path) -> None:
    """A store as schema v1 wrote it: commits without end_ts, no A/B columns."""
    conn = sqlite3.connect(path)
    conn.executescript(
        "CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);"
        "INSERT INTO meta VALUES ('schema', '1');"
        "CREATE TABLE commits(key TEXT, prompt_idx INT, ts REAL, sha TEXT,"
        " repo TEXT);"
        "INSERT INTO commits VALUES ('s1', 0, 5.0, 'abc', '/r');"
        "CREATE TABLE agent_calls(key TEXT, tool_use_id TEXT, agent_id TEXT,"
        " prompt_idx INT, ts REAL, description TEXT, subagent_type TEXT,"
        " model TEXT);"
        "INSERT INTO agent_calls VALUES ('s1','t','a',0,1.0,'d','x','m');"
    )
    conn.commit()
    conn.close()


def test_old_store_is_migrated_in_place_and_keeps_its_rows(tmp_path: Path) -> None:
    path = tmp_path / "t.sqlite"
    _v1_store(path)
    conn = schema.connect(path)
    kept = conn.execute("SELECT key, sha, end_ts FROM commits").fetchall()
    calls = conn.execute("SELECT tool_use_id, result_ts, status FROM agent_calls")
    version = conn.execute("SELECT value FROM meta WHERE key='schema'").fetchone()
    assert kept == [("s1", "abc", None)]
    assert calls.fetchall() == [("t", None, None)]
    assert version == (schema.VERSION,)
    conn.close()


def test_newer_store_is_refused_not_relabelled(tmp_path: Path) -> None:
    path = tmp_path / "t.sqlite"
    conn = sqlite3.connect(path)
    conn.executescript(
        "CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);"
        "INSERT INTO meta VALUES ('schema', '999');"
    )
    conn.commit()
    conn.close()
    with pytest.raises(schema.SchemaError):
        schema.connect(path)
    check = sqlite3.connect(path)
    assert check.execute("SELECT value FROM meta").fetchone() == ("999",)
    check.close()


def _meta_only(path: Path, version: str | None) -> None:
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT)")
    if version is not None:
        conn.execute("INSERT INTO meta VALUES ('schema', ?)", (version,))
    conn.commit()
    conn.close()


def test_meta_without_a_version_is_refused(tmp_path: Path) -> None:
    _meta_only(tmp_path / "t.sqlite", None)
    with pytest.raises(schema.SchemaError):
        schema.connect(tmp_path / "t.sqlite")


def test_table_missing_from_an_old_store_is_created_at_todays_shape(
    tmp_path: Path,
) -> None:
    _meta_only(tmp_path / "t.sqlite", "1")
    conn = schema.connect(tmp_path / "t.sqlite")
    columns = {r[1] for r in conn.execute("PRAGMA table_info(commits)")}
    conn.close()
    assert "end_ts" in columns
