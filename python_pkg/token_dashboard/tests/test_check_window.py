from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from python_pkg.token_dashboard import check_window, schema

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

DAY = 86400.0


def _store(tmp_path: Path, stamps: list[float]) -> Path:
    db = tmp_path / "t.sqlite"
    conn = schema.connect(db)
    conn.executemany(
        "INSERT INTO turns(key, ts, usd) VALUES ('k', ?, 1.0)", [(s,) for s in stamps]
    )
    conn.commit()
    conn.close()
    return db


def _snapshot(report: Path, name: str, metrics: Mapping[str, float]) -> None:
    folder = report / "history"
    folder.mkdir(parents=True, exist_ok=True)
    snap = {"window": {"since": 0, "until": 10 * DAY}, "metrics": metrics}
    (folder / f"{name}.json").write_text(json.dumps(snap), encoding="utf-8")


def _run(tmp_path: Path, db: Path, *extra: str) -> int:
    return check_window.main(
        ["--db", str(db), "--report-dir", str(tmp_path / "report"), *extra]
    )


def test_matching_snapshot_exits_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    db = _store(tmp_path, [100.0, 100.0 + DAY])
    good = {"usd_total": 2.0, "usd_per_day": 2.0, "calls": 2}
    _snapshot(tmp_path / "report", "2026-10-16", {**good, "calls": 99})
    _snapshot(tmp_path / "report", "2026-10-17", good)
    assert _run(tmp_path, db, "--snapshot", "2026-10-17") == 0
    out = capsys.readouterr().out
    assert out.count("OK") == 3
    assert "FAIL" not in out


def test_drift_beyond_one_percent_in_the_newest_snapshot_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    db = _store(tmp_path, [100.0, 100.0 + DAY])
    _snapshot(tmp_path / "report", "2026-10-16", {"usd_total": 2.0})
    bad = {"usd_total": 2.5, "usd_per_day": 2.0, "calls": 2}
    _snapshot(tmp_path / "report", "2026-10-17", bad)
    assert _run(tmp_path, db) == 1
    assert "usd_total: store 2.00 vs snapshot 2.50 (20.00%) FAIL" in (
        capsys.readouterr().out
    )


def test_empty_window_against_zero_metrics_is_a_match(tmp_path: Path) -> None:
    db = _store(tmp_path, [])
    zero = {"usd_total": 0, "usd_per_day": 0, "calls": 0}
    _snapshot(tmp_path / "report", "2026-10-17", zero)
    assert _run(tmp_path, db) == 0


def test_missing_snapshot_or_store_exits_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    db = _store(tmp_path, [1.0])
    assert _run(tmp_path, db) == 1  # no snapshot directory at all
    _snapshot(tmp_path / "report", "2026-10-17", {"usd_total": 1})
    assert _run(tmp_path, db, "--snapshot", "1999-01-01") == 1
    assert _run(tmp_path, tmp_path / "gone.sqlite") == 1
    assert capsys.readouterr().err.count("missing snapshot or store") == 3
