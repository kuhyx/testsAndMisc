"""BACKLOG parsing and done dates recovered from the Firebase dumps."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from python_pkg.token_audit import notes_backlog
from python_pkg.token_audit.tests import test_notes_fixtures as fx

if TYPE_CHECKING:
    from pathlib import Path


def _ts(iso: str) -> float:
    return datetime.fromisoformat(iso).replace(tzinfo=UTC).timestamp()


def test_parse_reads_ids_status_title(tmp_path: Path) -> None:
    text = fx.backlog(tmp_path / "BACKLOG.md").read_text()
    notes = notes_backlog.parse_backlog(text)
    assert [n.id for n in notes] == [fx.NOTE_A, fx.NOTE_B, fx.NOTE_C, fx.NOTE_D]
    assert notes[0].status == "done"
    assert notes[0].title == "diet guard meal times picker"
    assert notes[1].status == "abandoned"
    assert notes[0].updated is not None


def test_unknown_status_falls_back_to_todo() -> None:
    text = '<!-- @note id="x" status="weird" -->\nbody'
    assert notes_backlog.parse_backlog(text)[0].status == "todo"


def test_hlc_time_parses_prefix_and_rejects_junk() -> None:
    assert notes_backlog.hlc_time("2026-10-01T10:00:00.000Z-0000-dev") == _ts(
        "2026-10-01T10:00:00"
    )
    assert notes_backlog.hlc_time("nonsense") is None
    assert notes_backlog.hlc_time(None) is None


def test_done_at_is_status_hlc_of_first_dump_showing_done(tmp_path: Path) -> None:
    dumps = tmp_path / "dumps"
    fx.dump(dumps, "2026-10-01T000000Z", {fx.NOTE_A: (1, "2026-09-30T08:00:00.000Z")})
    fx.dump(dumps, "2026-10-02T000000Z", {fx.NOTE_A: (2, "2026-10-01T12:00:00.000Z")})
    # Re-stamped later by an unrelated upsert: must not move the done date.
    fx.dump(dumps, "2026-10-03T000000Z", {fx.NOTE_A: (2, "2026-10-02T20:00:00.000Z")})
    notes = notes_backlog.load_notes(fx.backlog(tmp_path / "B.md"), dumps)
    done = {n.id: n.done_at for n in notes}
    assert done[fx.NOTE_A] == _ts("2026-10-01T12:00:00")


def test_device_with_newest_hlc_wins(tmp_path: Path) -> None:
    dumps = tmp_path / "dumps"
    path = fx.dump(dumps, "2026-10-02T000000Z", {})
    first = notes_backlog.merge_devices(
        {
            "d1": '{"n": {"fields": {"status": [2, "2026-10-01T00:00:00.000Z-0-d1"]}}}',
            "d2": '{"n": {"fields": {"status": [0, "2026-09-01T00:00:00.000Z-0-d2"]}}}',
            "d3": '{"gone": {"deleted": true, "fields": {"status": [2, "x"]}}}',
            "d4": "not json",
        }
    )
    assert first == {"n": (2, "2026-10-01T00:00:00.000Z-0-d1")}
    assert path.exists()


def test_abandoned_dated_from_dump_and_todo_has_no_date(tmp_path: Path) -> None:
    dumps = tmp_path / "dumps"
    fx.dump(dumps, "2026-10-05T000000Z", {fx.NOTE_B: (3, "2026-10-04T09:00:00.000Z")})
    notes = {
        n.id: n for n in notes_backlog.load_notes(fx.backlog(tmp_path / "B.md"), dumps)
    }
    assert notes[fx.NOTE_B].done_at == _ts("2026-10-04T09:00:00")
    assert notes[fx.NOTE_C].done_at is None


def test_fallback_to_backlog_updated_when_no_dump_has_it(tmp_path: Path) -> None:
    notes = {
        n.id: n
        for n in notes_backlog.load_notes(
            fx.backlog(tmp_path / "B.md"), tmp_path / "none"
        )
    }
    assert notes[fx.NOTE_D].done_at == notes[fx.NOTE_D].updated
    assert notes[fx.NOTE_D].done_at is not None


def test_unreadable_dump_is_skipped(tmp_path: Path) -> None:
    dumps = tmp_path / "dumps"
    dumps.mkdir()
    (dumps / "kuhy-syncs-2026-10-01T000000Z.json.gz").write_bytes(b"not gzip")
    notes = notes_backlog.load_notes(fx.backlog(tmp_path / "B.md"), dumps)
    assert len(notes) == 4
