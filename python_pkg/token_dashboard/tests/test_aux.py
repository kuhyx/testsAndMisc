from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import TYPE_CHECKING

import pytest

from python_pkg.token_dashboard import aux, schema
from python_pkg.token_dashboard.tests.test_levers import TABLE

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence
    from pathlib import Path
    import sqlite3

NOON = datetime(2026, 10, 9, 12, tzinfo=UTC)
SECONDS = NOON.timestamp()


def _lines(path: Path, rows: Sequence[object], *junk: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = [json.dumps(r) for r in rows] + list(junk)
    path.write_text("\n".join(body) + "\n", encoding="utf-8")


@pytest.fixture
def conn(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    opened = schema.connect(tmp_path / "t.sqlite")
    yield opened
    opened.close()


def test_jsonl_skips_blank_malformed_and_non_object_lines(tmp_path: Path) -> None:
    path = tmp_path / "x.jsonl"
    _lines(path, [{"a": 1}, [1, 2], 3], "", "{broken")
    assert list(aux._jsonl(path)) == [{"a": 1}]
    assert list(aux._jsonl(tmp_path / "missing.jsonl")) == []


def test_stamp_reads_iso_seconds_milliseconds_and_rejects_the_rest() -> None:
    assert aux._stamp(NOON.isoformat()) == SECONDS
    assert aux._stamp(SECONDS) == SECONDS
    assert aux._stamp(int(SECONDS * 1000)) == pytest.approx(int(SECONDS))
    assert aux._stamp("yesterday") is None
    assert aux._stamp(["x"]) is None
    assert aux._stamp(None) is None


def test_snapshots_copy_window_and_metrics_and_skip_unreadable(
    tmp_path: Path, conn: sqlite3.Connection
) -> None:
    history = tmp_path / "report" / "history"
    history.mkdir(parents=True)
    snap = {
        "generated": NOON.isoformat(),
        "window": {"since": 1.0, "until": 2.0},
        "metrics": {"usd_total": 5},
    }
    (history / "2026-10-09.json").write_text(json.dumps(snap))
    (history / "2026-10-10.json").write_text("{not json")
    aux.snapshots(conn, tmp_path / "report")
    rows = conn.execute("SELECT name, since, until, metrics FROM snapshots").fetchall()
    assert rows == [("2026-10-09", 1.0, 2.0, '{"usd_total": 5}')]


def test_lever_rows_assign_each_table_to_the_nearest_snapshot(
    tmp_path: Path, conn: sqlite3.Connection
) -> None:
    report = tmp_path / "report"
    (report / "history").mkdir(parents=True)
    for day in ("2026-10-02", "2026-10-09"):
        stamp = datetime.fromisoformat(f"{day}T12:00:00+00:00").isoformat()
        (report / "history" / f"{day}.json").write_text(
            json.dumps({"generated": stamp})
        )
    (report / "WEEKLY.md").write_text(TABLE, encoding="utf-8")
    aux.snapshots(conn, report)
    conn.execute("INSERT INTO lever_tables VALUES ('s', ?, ?)", (SECONDS, TABLE))
    aux.lever_rows(conn, report)
    sources = {r[0] for r in conn.execute("SELECT source FROM levers")}
    assert "snapshot 2026-10-09" in sources


def test_lever_rows_with_no_snapshots_store_nothing(
    tmp_path: Path, conn: sqlite3.Connection
) -> None:
    conn.execute("INSERT INTO lever_tables VALUES ('s', ?, ?)", (SECONDS, TABLE))
    aux.lever_rows(conn, tmp_path / "report")
    assert conn.execute("SELECT COUNT(*) FROM levers").fetchone() == (0,)


def _autopsy_row(
    sid: str, started: object, msgs: int, api: int | None
) -> dict[str, object]:
    return {
        "session_id": sid,
        "meta": {"started_at": started, "cwd": "/r", "title": sid},
        "tokens": {"input": 100, "cache_write": 200, "cache_read": 300, "output": 400},
        "turns": {"api_turns": api},
        "counts": {"assistant_msgs": msgs},
    }


def test_autopsy_scales_by_api_turns_and_calibrates_against_transcripts(
    conn: sqlite3.Connection,
) -> None:
    rows = [
        _autopsy_row("both", NOON.isoformat(), 10, 5),
        _autopsy_row("alone", SECONDS, 4, None),
        _autopsy_row("nostart", None, 4, 2),
        _autopsy_row("nomsgs", SECONDS, 0, 0),
    ]
    _lines(aux.AUTOPSY, rows)
    conn.execute("INSERT INTO session_summary(key, usd_main) VALUES ('both', 3.0)")
    aux.autopsy(conn)
    got = dict(conn.execute("SELECT session_id, usd_est FROM aggregate_sessions"))
    assert set(got) == {"both", "alone"}
    # Same tokens: 5 API turns over 10 records scales the cost by one half.
    assert got["both"] == pytest.approx(got["alone"] / 2)
    factor = conn.execute("SELECT value FROM meta WHERE key='autopsy_calibration'")
    assert float(factor.fetchone()[0]) == pytest.approx(3.0 / got["both"])


def test_autopsy_without_overlap_keeps_factor_one(conn: sqlite3.Connection) -> None:
    aux.autopsy(conn)
    factor = conn.execute("SELECT value FROM meta WHERE key='autopsy_calibration'")
    assert factor.fetchone() == ("1.0",)


def test_activity_logs_count_prompts_events_and_first_estimate(
    tmp_path: Path, conn: sqlite3.Connection
) -> None:
    report = tmp_path / "report"
    _lines(
        aux.PROMPT_HISTORY,
        [{"timestamp": int(SECONDS * 1000)}, {"timestamp": SECONDS}, {"x": 1}],
    )
    _lines(aux.TIME_CAP, [{"ts": SECONDS, "event": "kill", "command": "sleep 99"}])
    misses = report / "task-size" / "misses.jsonl"
    _lines(misses, [{"ts": NOON.isoformat(), "kind": "under", "first_prompt": "p"}])
    verdicts = [
        {"status": "ok", "session": "a", "verdict": {"est_calls": 12}},
        {"status": "ok", "session": "a", "verdict": {"est_calls": 99}},
        {"status": "ok", "session": "b", "verdict": "none"},
        {"status": "error", "session": "c", "verdict": {"est_calls": 3}},
    ]
    _lines(report / "task-size" / "verdicts.jsonl", verdicts)
    aux.activity_logs(conn, report)
    days = conn.execute("SELECT prompts FROM prompt_activity").fetchall()
    events = conn.execute("SELECT source, kind, detail FROM events").fetchall()
    estimates = conn.execute("SELECT session_id, est_calls FROM estimates").fetchall()
    assert days == [(2,)]
    assert events == [
        ("time-cap", "kill", "sleep 99"),
        ("task-size-miss", "under", "p"),
    ]
    assert estimates == [("a", 12)]


def test_reloading_keeps_rows_a_trimmed_source_no_longer_has(tmp_path: Path) -> None:
    conn = schema.connect(tmp_path / "t.sqlite")
    _lines(
        aux.PROMPT_HISTORY,
        [{"timestamp": 1_700_000_000_000}, {"timestamp": 1_800_000_000}],
    )
    aux.activity_logs(conn, tmp_path / "report")
    aux.PROMPT_HISTORY.write_text("", encoding="utf-8")  # rotated away
    aux.activity_logs(conn, tmp_path / "report")
    aux.activity_logs(conn, tmp_path / "report")
    days = conn.execute("SELECT COUNT(*), SUM(prompts) FROM prompt_activity").fetchone()
    conn.close()
    assert days == (2, 2)
