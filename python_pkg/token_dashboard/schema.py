"""SQLite layout of the durable token store.

Raw tables (``files`` .. ``commits``) hold what one transcript file said and
are replaced wholesale when that file changes. They are **never** deleted when
the file disappears: Claude Code removes transcripts after
``cleanupPeriodDays``, and outliving that is the store's whole purpose.

Summary tables (``session_summary`` .. ``subagent_link``) are derived from the
raw ones by :mod:`finalize` and may be rebuilt at any time. Aux tables hold the
sources that are not transcripts (snapshots, ledger, levers, autopsy rows).
"""

from __future__ import annotations

from pathlib import Path
import sqlite3

DEFAULT_DB = Path.home() / "data" / "token-dashboard" / "tokens.sqlite"
VERSION = "3"

_RAW = """
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS files(
    path TEXT PRIMARY KEY, key TEXT, size INT, mtime REAL);
CREATE TABLE IF NOT EXISTS sessions(
    key TEXT PRIMARY KEY, session_id TEXT, main_key TEXT, cwd TEXT,
    agent_type TEXT, description TEXT, spawn_tool_use_id TEXT,
    parent_agent_id TEXT, agent_model TEXT, first_ts REAL, last_ts REAL,
    final_tag TEXT);
CREATE TABLE IF NOT EXISTS turns(
    key TEXT, main_key TEXT, is_sub INT, cwd TEXT, ts REAL, day TEXT,
    model TEXT, usd REAL, context INT, prompt_idx INT, input INT,
    cache_write INT, cache_read INT, output INT);
CREATE INDEX IF NOT EXISTS turns_key ON turns(key);
CREATE INDEX IF NOT EXISTS turns_day ON turns(day);
CREATE TABLE IF NOT EXISTS prompts(
    key TEXT, idx INT, ts REAL, prompt_id TEXT, text TEXT);
CREATE INDEX IF NOT EXISTS prompts_key ON prompts(key);
CREATE TABLE IF NOT EXISTS tool_use(
    key TEXT, prompt_idx INT, name TEXT, calls INT, result_tokens INT,
    usd REAL, carry_usd REAL);
CREATE INDEX IF NOT EXISTS tool_use_key ON tool_use(key);
CREATE TABLE IF NOT EXISTS agent_calls(
    key TEXT, tool_use_id TEXT, agent_id TEXT, prompt_idx INT, ts REAL,
    description TEXT, subagent_type TEXT, model TEXT, result_ts REAL,
    status TEXT);
CREATE INDEX IF NOT EXISTS agent_calls_key ON agent_calls(key);
CREATE TABLE IF NOT EXISTS activity(key TEXT, start REAL, end REAL);
CREATE INDEX IF NOT EXISTS activity_key ON activity(key);
CREATE TABLE IF NOT EXISTS sent_messages(key TEXT, ts REAL, to_agent TEXT);
CREATE TABLE IF NOT EXISTS lever_tables(key TEXT, ts REAL, markdown TEXT);
CREATE TABLE IF NOT EXISTS commits(
    key TEXT, prompt_idx INT, ts REAL, end_ts REAL, sha TEXT, repo TEXT);
CREATE TABLE IF NOT EXISTS calls(
    key TEXT, main_key TEXT, is_sub INT, cwd TEXT, model TEXT, ts REAL,
    day TEXT, prompt_idx INT, end_ts REAL, name TEXT, family TEXT,
    target TEXT, sig TEXT, batch INT, result_tokens INT, images INT,
    is_error INT, error_kind TEXT, create_usd REAL, carry_usd REAL,
    carry_calls INT);
CREATE INDEX IF NOT EXISTS calls_key ON calls(key);
CREATE INDEX IF NOT EXISTS calls_ts ON calls(ts);
CREATE TABLE IF NOT EXISTS marks(
    key TEXT, main_key TEXT, is_sub INT, cwd TEXT, model TEXT, ts REAL,
    day TEXT, prompt_idx INT, kind TEXT, name TEXT, detail TEXT, count INT,
    tokens INT, extra INT, duration_ms INT, retry_usd REAL, create_usd REAL,
    carry_usd REAL, carry_calls INT);
CREATE INDEX IF NOT EXISTS marks_key ON marks(key);
CREATE INDEX IF NOT EXISTS marks_ts ON marks(ts);
CREATE TABLE IF NOT EXISTS turn_detail(
    key TEXT, main_key TEXT, is_sub INT, cwd TEXT, model TEXT, ts REAL,
    day TEXT, prompt_idx INT, latency_s REAL, cw_1h INT, cw_5m INT,
    out_text INT, out_tool INT, out_think INT, tool_calls INT);
CREATE INDEX IF NOT EXISTS turn_detail_key ON turn_detail(key);
CREATE INDEX IF NOT EXISTS turn_detail_ts ON turn_detail(ts);
CREATE TABLE IF NOT EXISTS session_commits(
    sha TEXT PRIMARY KEY, repo TEXT, ts REAL, key TEXT, prompt_idx INT);
"""

_DERIVED = """
CREATE TABLE IF NOT EXISTS session_summary(
    key TEXT PRIMARY KEY, cwd TEXT, title TEXT, first_ts REAL, last_ts REAL,
    wall_s REAL, active_s REAL, usd REAL, usd_main REAL, usd_sub REAL,
    calls INT, prompts INT, subagents INT, models TEXT, final_tag TEXT);
CREATE TABLE IF NOT EXISTS prompt_summary(
    key TEXT, idx INT, ts REAL, text TEXT, usd_own REAL, usd_sub REAL,
    active_s REAL, wall_s REAL, calls INT);
CREATE INDEX IF NOT EXISTS prompt_summary_key ON prompt_summary(key);
CREATE TABLE IF NOT EXISTS subagent_link(
    sub_key TEXT PRIMARY KEY, main_key TEXT, prompt_idx INT, depth INT,
    description TEXT, agent_type TEXT, model TEXT, usd REAL, calls INT,
    first_ts REAL, last_ts REAL, wall_s REAL, active_s REAL);
CREATE INDEX IF NOT EXISTS subagent_link_main ON subagent_link(main_key);
CREATE TABLE IF NOT EXISTS commit_verdicts(
    sha TEXT PRIMARY KEY, repo TEXT, ts REAL, added INT, kept INT,
    verdict TEXT);
CREATE VIEW IF NOT EXISTS daily AS
    SELECT day, SUM(usd) AS usd, COUNT(*) AS calls,
        SUM(CASE WHEN is_sub THEN usd ELSE 0 END) AS usd_sub,
        SUM(CASE WHEN model LIKE '%opus%' THEN usd ELSE 0 END) AS usd_opus,
        SUM(CASE WHEN context > 300000 THEN usd ELSE 0 END) AS usd_over
    FROM turns GROUP BY day;
"""

_AUX = """
CREATE TABLE IF NOT EXISTS snapshots(
    name TEXT PRIMARY KEY, generated TEXT, since REAL, until REAL,
    metrics TEXT);
CREATE TABLE IF NOT EXISTS levers(
    source TEXT, date TEXT, lever TEXT, metric TEXT, baseline REAL,
    predicted REAL, actual REAL, lower_is_better INT, status TEXT,
    outcome TEXT, detail TEXT);
CREATE TABLE IF NOT EXISTS aggregate_sessions(
    session_id TEXT PRIMARY KEY, source TEXT, day TEXT, started REAL,
    cwd TEXT, title TEXT, input INT, cache_write INT, cache_read INT,
    output INT, api_turns INT, records INT, usd_est REAL);
CREATE TABLE IF NOT EXISTS prompt_activity(day TEXT PRIMARY KEY, prompts INT);
CREATE TABLE IF NOT EXISTS events(source TEXT, ts REAL, kind TEXT, detail TEXT);
CREATE UNIQUE INDEX IF NOT EXISTS events_once ON events(source, ts, kind, detail);
CREATE TABLE IF NOT EXISTS context_files(
    path TEXT PRIMARY KEY, kind TEXT, standing TEXT, size_limit INT);
CREATE TABLE IF NOT EXISTS context_sizes(
    path TEXT, ts REAL, bytes INT, source TEXT, PRIMARY KEY (path, ts, source));
CREATE TABLE IF NOT EXISTS estimates(session_id TEXT PRIMARY KEY, est_calls INT);
"""


# Ordered, additive migrations: MIGRATIONS[n] takes a store from n-1 to n.
# The store must never be deleted to change its schema -- rows for expired
# transcripts cannot be regenerated -- so every change lands here instead.
# New tables need no entry: CREATE TABLE IF NOT EXISTS adds them.
MIGRATIONS: dict[int, tuple[str, ...]] = {
    2: ("ALTER TABLE commits ADD COLUMN end_ts REAL",),
    3: (
        "ALTER TABLE agent_calls ADD COLUMN result_ts REAL",
        "ALTER TABLE agent_calls ADD COLUMN status TEXT",
    ),
}


class SchemaError(RuntimeError):
    """The store was written by a newer (or unknown) schema."""

    def __init__(self, found: object) -> None:
        """Name the version found and the one this code knows."""
        super().__init__(f"store schema {found!r}; this code knows {VERSION}")


def _stored_version(conn: sqlite3.Connection) -> int | None:
    """The schema the store was written with, ``None`` for a fresh file."""
    has_meta = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='meta'"
    ).fetchone()
    if has_meta is None:
        return None
    row = conn.execute("SELECT value FROM meta WHERE key='schema'").fetchone()
    if row is None or not str(row[0]).isdigit():
        raise SchemaError(row)
    return int(row[0])


def _migrate(conn: sqlite3.Connection, stored: int) -> None:
    """Apply every migration newer than ``stored``, in order."""
    current = int(VERSION)
    if stored > current:
        raise SchemaError(stored)
    for step in range(stored + 1, current + 1):
        for statement in MIGRATIONS.get(step, ()):
            table, column = statement.split()[2], statement.split()[5]
            present = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
            if column not in present:
                conn.execute(statement)


def connect(path: Path, *, readonly: bool = False) -> sqlite3.Connection:
    """Open the store; create missing tables and migrate when writing."""
    if readonly:
        return sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        stored = _stored_version(conn)
        # Missing tables first, at today's shape; then columns old tables lack.
        conn.executescript(_RAW + _DERIVED + _AUX)
        if stored is not None:
            _migrate(conn, stored)
    except SchemaError:
        conn.close()
        raise
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("INSERT OR REPLACE INTO meta VALUES ('schema', ?)", (VERSION,))
    conn.commit()
    return conn
