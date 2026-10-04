from __future__ import annotations

import json
from pathlib import Path

from python_pkg.token_audit import history


def test_save_snapshot_never_overwrites(tmp_path: Path) -> None:
    first = history.save_snapshot({"n": 1}, tmp_path)
    second = history.save_snapshot({"n": 2}, tmp_path)
    assert first != second
    assert json.loads(first.read_text(encoding="utf-8")) == {"n": 1}
    assert json.loads(second.read_text(encoding="utf-8")) == {"n": 2}
    assert first.parent == tmp_path / history.HISTORY_NAME


def test_default_directory_is_redirected_report_dir() -> None:
    path = history.save_snapshot({"n": 1})
    assert path.is_relative_to(history.REPORT_DIR)
    assert history.last_snapshot() == {"n": 1}


def test_last_snapshot_none_without_folder(tmp_path: Path) -> None:
    assert history.last_snapshot(tmp_path) is None
    assert history.default_since(tmp_path) is None


def test_last_snapshot_skips_unreadable_and_non_dict(tmp_path: Path) -> None:
    folder = tmp_path / history.HISTORY_NAME
    folder.mkdir()
    (folder / "2026-01-01.json").write_text('{"ok": true}', encoding="utf-8")
    (folder / "2026-01-02.json").write_text("[1]", encoding="utf-8")
    (folder / "2026-01-03.json").write_text("garbage", encoding="utf-8")
    assert history.last_snapshot(tmp_path) == {"ok": True}


def test_last_snapshot_none_when_nothing_usable(tmp_path: Path) -> None:
    folder = tmp_path / history.HISTORY_NAME
    folder.mkdir()
    (folder / "2026-01-01.json").write_text("garbage", encoding="utf-8")
    assert history.last_snapshot(tmp_path) is None


def test_default_since_reads_window_end(tmp_path: Path) -> None:
    history.save_snapshot({"window": {"until": 123.5}}, tmp_path)
    assert history.default_since(tmp_path) == 123.5


def test_default_since_none_when_until_not_numeric(tmp_path: Path) -> None:
    history.save_snapshot({"window": {"until": "soon"}}, tmp_path)
    assert history.default_since(tmp_path) is None


def test_read_ledger_missing_file(tmp_path: Path) -> None:
    assert history.read_ledger(tmp_path) == []


def test_append_and_read_ledger_filters_bad_lines(tmp_path: Path) -> None:
    target = tmp_path / "nested"
    history.append_ledger({"metric": "m", "baseline": 1.0}, target)
    history.append_ledger(
        {"metric": "m", "baseline": 2.0, "date": "2020-01-01"}, target
    )
    ledger = target / history.LEDGER_NAME
    with ledger.open("a", encoding="utf-8") as handle:
        handle.write("garbage\n[1]\n" + json.dumps({"metric": "only"}) + "\n")
    entries = history.read_ledger(target)
    assert [e["baseline"] for e in entries] == [1.0, 2.0]
    assert entries[1]["date"] == "2020-01-01"
    assert len(entries[0]["date"]) == len("2026-10-04")


def test_append_ledger_default_directory() -> None:
    history.append_ledger({"metric": "m", "baseline": 1})
    assert len(history.read_ledger()) == 1
