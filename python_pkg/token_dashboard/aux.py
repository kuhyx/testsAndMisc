"""Non-transcript sources: snapshots, levers, autopsy aggregates, activity logs.

Each loader is idempotent (it replaces its own rows) and cheap, so every
complete ingest pass reruns all of them.

The session-autopsy cache (``~/.claude/autopsy/sessions.jsonl``) is the only
source of per-session numbers for transcripts already deleted. It is
**aggregate only**: tokens are summed per transcript record, not per API
message (about 2x), there is no model split and no subagents. It is therefore
scaled by ``api_turns / assistant_msgs``, priced as Opus 5.5, and then
calibrated against sessions present in both sources (``meta`` key
``autopsy_calibration``). It is never mixed into the per-session tables.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from python_pkg.token_audit import pricing
from python_pkg.token_dashboard import levers, store

if TYPE_CHECKING:
    from collections.abc import Iterator
    import sqlite3

CLAUDE = Path.home() / ".claude"
AUTOPSY = CLAUDE / "autopsy" / "sessions.jsonl"
PROMPT_HISTORY = CLAUDE / "history.jsonl"
TIME_CAP = CLAUDE / "logs" / "time-cap.jsonl"
_MS = 1000.0
_MS_EPOCH = 1e11  # anything larger is milliseconds, not seconds


def _jsonl(path: Path) -> Iterator[dict[str, Any]]:
    """Well-formed object lines of a JSONL file (none if it is missing)."""
    if not path.is_file():
        return
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if isinstance(row, dict):
                yield row


def _stamp(raw: object) -> float | None:
    """ISO string or epoch (s or ms) to unix seconds."""
    if isinstance(raw, (int, float)):
        return raw / _MS if raw > _MS_EPOCH else float(raw)
    if isinstance(raw, str):
        try:
            return datetime.fromisoformat(raw).timestamp()
        except ValueError:
            return None
    return None


def snapshots(conn: sqlite3.Connection, report: Path) -> None:
    """Copy every history snapshot's window and metrics."""
    for path in sorted((report / "history").glob("*.json")):
        try:
            snap = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            continue
        window = snap.get("window", {})
        conn.execute(
            "INSERT OR REPLACE INTO snapshots VALUES (?,?,?,?,?)",
            (
                path.stem,
                snap.get("generated"),
                window.get("since"),
                window.get("until"),
                json.dumps(snap.get("metrics", {})),
            ),
        )


def _nearest(generated: list[tuple[float, str]], stamp: float) -> str:
    """The snapshot day generated closest to ``stamp``."""
    return min(generated, key=lambda g: abs(g[0] - stamp))[1]


def lever_rows(conn: sqlite3.Connection, report: Path) -> None:
    """Rebuild the ``levers`` table from every source."""
    generated = [
        (_stamp(g) or 0.0, name[:10])
        for name, g in conn.execute("SELECT name, generated FROM snapshots")
    ]
    tables: dict[str, str] = {}
    found = conn.execute("SELECT ts, markdown FROM lever_tables ORDER BY ts")
    weekly = report / "WEEKLY.md"
    extra = []
    if weekly.is_file():
        extra = [(weekly.stat().st_mtime, weekly.read_text(encoding="utf-8"))]
    for ts, markdown in [*found, *extra]:
        # A table belongs to the snapshot generated closest to it.
        if generated:
            tables.setdefault(_nearest(generated, ts), markdown)
    conn.execute("DELETE FROM levers")
    conn.executemany(
        "INSERT INTO levers VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        [tuple(row.values()) for row in levers.build(report, tables)],
    )


def autopsy(conn: sqlite3.Connection) -> None:
    """Load autopsy aggregates and calibrate their dollar estimate."""
    price = pricing.load().for_model("claude-opus-5-5")
    for row in _jsonl(AUTOPSY):
        meta, tok, turns = (
            row.get("meta", {}),
            row.get("tokens", {}),
            row.get("turns", {}),
        )
        started = _stamp(meta.get("started_at"))
        records = row.get("counts", {}).get("assistant_msgs") or 0
        api = turns.get("api_turns") or records
        if started is None or not records:
            continue
        scale = api / records
        raw = (
            tok.get("input", 0) * price.input
            + tok.get("cache_write", 0) * price.input * pricing.WRITE_1H
            + tok.get("cache_read", 0) * price.cache_read
            + tok.get("output", 0) * price.output
        ) / pricing.PER_MILLION
        conn.execute(
            "INSERT OR REPLACE INTO aggregate_sessions VALUES"
            " (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                row.get("session_id"),
                "autopsy",
                store.day_of(started),
                started,
                meta.get("cwd"),
                meta.get("title"),
                tok.get("input", 0),
                tok.get("cache_write", 0),
                tok.get("cache_read", 0),
                tok.get("output", 0),
                api,
                records,
                raw * scale,
            ),
        )
    est, real = conn.execute(
        "SELECT SUM(a.usd_est), SUM(s.usd_main) FROM aggregate_sessions a"
        " JOIN session_summary s ON s.key = a.session_id"
    ).fetchone()
    factor = (real / est) if est and real else 1.0
    conn.execute(
        "INSERT OR REPLACE INTO meta VALUES ('autopsy_calibration', ?)", (str(factor),)
    )


def activity_logs(conn: sqlite3.Connection, report: Path) -> None:
    """Prompt counts per day, time-cap events, task-size misses and estimates."""
    days: Counter[str] = Counter()
    for row in _jsonl(PROMPT_HISTORY):
        stamp = _stamp(row.get("timestamp"))
        if stamp is not None:
            days[store.day_of(stamp)] += 1
    # Upserts, never a wipe: if history.jsonl is trimmed, the days it lost stay.
    conn.executemany(
        "INSERT INTO prompt_activity VALUES (?,?) ON CONFLICT(day) DO UPDATE"
        " SET prompts = MAX(prompts, excluded.prompts)",
        days.items(),
    )
    sources = (
        ("time-cap", TIME_CAP, "event"),
        ("task-size-miss", report / "task-size" / "misses.jsonl", "kind"),
    )
    for name, path, kind_key in sources:
        conn.executemany(
            "INSERT OR IGNORE INTO events VALUES (?,?,?,?)",
            [
                (
                    name,
                    _stamp(r.get("ts")),
                    str(r.get(kind_key)),
                    str(r.get("command") or r.get("first_prompt") or "")[:200],
                )
                for r in _jsonl(path)
            ],
        )
    for row in _jsonl(report / "task-size" / "verdicts.jsonl"):
        verdict = row.get("verdict")
        calls = verdict.get("est_calls") if isinstance(verdict, dict) else None
        if row.get("status") == "ok" and isinstance(calls, int):
            # The first sized prompt of a session is its pre-work estimate.
            conn.execute(
                "INSERT OR IGNORE INTO estimates VALUES (?,?)",
                (row.get("session"), calls),
            )
