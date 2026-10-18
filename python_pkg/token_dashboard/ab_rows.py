"""Per-assignment A/B outcomes, so the dashboard can filter the A/B panel.

:func:`ab.rebuild` summarises all assignments into ``meta['ab']`` (the
all-time verdict). This module also keeps one row per joined assignment, with
the parent call's session, cwd, model and scope, so a cwd / model / scope
filter can recount the arms. Derived: replaced wholesale on every rebuild.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS ab_rows(
    tool_use_id TEXT PRIMARY KEY, arm TEXT, key TEXT, main_key TEXT, is_sub INT,
    cwd TEXT, model TEXT, ts REAL, usd REAL, duration_s REAL, redo INT,
    followup INT, error INT, correction INT, tag TEXT);
"""


def store(
    conn: sqlite3.Connection, joined: list[tuple[str, str, dict[str, Any]]]
) -> None:
    """Replace every row with ``(arm, tool_use_id, outcome)`` triples."""
    conn.executescript(SCHEMA)
    conn.execute("DELETE FROM ab_rows")
    for arm, tool_use_id, found in joined:
        key = str(found["key"])
        where = conn.execute(
            "SELECT cwd, model FROM turns WHERE key = ? AND ts <= ?"
            " ORDER BY ts DESC LIMIT 1",
            (key, found["ts"]),
        ).fetchone() or (None, None)
        conn.execute(
            "INSERT OR REPLACE INTO ab_rows VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                tool_use_id,
                arm,
                key,
                key.split("/", 1)[0],
                int("/" in key),
                where[0],
                where[1],
                found["ts"],
                found["usd"],
                found["duration_s"],
                int(found["redo"]),
                int(found["followup"]),
                int(found["error"]),
                int(found["correction"]),
                found["tag"],
            ),
        )
