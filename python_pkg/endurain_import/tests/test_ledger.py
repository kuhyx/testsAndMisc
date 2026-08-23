"""Ledger behaviour, especially the two independent dedupe paths."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from python_pkg.endurain_import.ledger import (
    Entry,
    Ledger,
    LedgerCorruptError,
    activity_key,
    file_digest,
    now_iso,
)


def _entry(sha: str = "abc", key: str = "RunnerUp_ts_Running") -> Entry:
    return Entry(sha, key, "f.tcx", 7, now_iso())


def test_digest_is_content_addressed(tmp_path: Path) -> None:
    a = tmp_path / "a.tcx"
    b = tmp_path / "b.tcx"
    a.write_text("same")
    b.write_text("same")
    assert file_digest(a) == file_digest(b)

    b.write_text("different")
    assert file_digest(a) != file_digest(b)


def test_activity_key_collapses_export_formats() -> None:
    """The .gpx and .tcx of one run must share a key."""
    tcx = Path("RunnerUp_2026-08-22-23-51-04_Running.tcx")
    gpx = Path("RunnerUp_2026-08-22-23-51-04_Running.gpx")
    assert activity_key(tcx) == activity_key(gpx)


def test_activity_key_ignores_device_model() -> None:
    """WebDAV names embed Build.MODEL; adb names do not."""
    webdav = Path("RunnerUp_Pixel_6a_2026-08-22-23-51-04_Running.tcx")
    adb = Path("RunnerUp_2026-08-22-23-51-04_Running.tcx")
    assert activity_key(webdav) == activity_key(adb)


def test_activity_key_separates_distinct_runs() -> None:
    first = Path("RunnerUp_2026-08-22-23-51-04_Running.tcx")
    second = Path("RunnerUp_2026-08-19-19-10-04_Running.tcx")
    assert activity_key(first) != activity_key(second)


def test_activity_key_falls_back_to_stem() -> None:
    assert activity_key(Path("whatever.tcx")) == "whatever"


def test_record_and_membership(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "l.json")
    assert len(ledger) == 0
    ledger.record(_entry())
    assert "abc" in ledger
    assert ledger.has_activity("RunnerUp_ts_Running")
    assert not ledger.has_activity("other")
    assert len(ledger) == 1


def test_ledger_survives_reload(tmp_path: Path) -> None:
    path = tmp_path / "l.json"
    Ledger(path).record(_entry())
    assert "abc" in Ledger(path)


def test_corrupt_ledger_fails_closed(tmp_path: Path) -> None:
    """A truncated ledger must stop the run, not re-import everything."""
    path = tmp_path / "l.json"
    path.write_text("{not json")
    with pytest.raises(LedgerCorruptError):
        Ledger(path)


def test_write_is_atomic(tmp_path: Path) -> None:
    path = tmp_path / "l.json"
    ledger = Ledger(path)
    ledger.record(_entry())
    assert not path.with_suffix(".tmp").exists()
    assert json.loads(path.read_text())["abc"]["activity_id"] == 7


def test_non_dict_ledger_is_ignored(tmp_path: Path) -> None:
    """A JSON list is valid JSON but not a ledger; treat it as empty."""
    path = tmp_path / "l.json"
    path.write_text("[]")
    assert len(Ledger(path)) == 0
