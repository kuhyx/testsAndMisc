"""USD per completed note: the split, the window rules and the outputs."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import TYPE_CHECKING

from python_pkg.token_audit import notes, notes_backlog, notes_cost
from python_pkg.token_audit.notes_link import Link
from python_pkg.token_audit.tests import test_notes_fixtures as fx

if TYPE_CHECKING:
    from pathlib import Path

NOTE_E = "eeeeeeee-5555-4555-8555-000000000005"


def _ts(iso: str) -> float:
    return datetime.fromisoformat(iso).replace(tzinfo=UTC).timestamp()


def _note(note_id: str, status: str, done: str | None) -> notes_backlog.Note:
    stamp = _ts(done) if done else None
    title = f"title of {note_id[:4]} " + "x" * 80
    return notes_backlog.Note(note_id, title, title, "high", status, stamp, stamp)


NOTES = [
    _note(fx.NOTE_A, "done", "2026-10-20T00:00:00"),
    _note(fx.NOTE_B, "abandoned", "2026-10-21T00:00:00"),
    _note(fx.NOTE_C, "todo", None),
    _note(fx.NOTE_D, "done", "2026-09-01T00:00:00"),
    _note(NOTE_E, "done", "2026-10-22T00:00:00"),
]
LINKS = {
    "s1": Link((fx.NOTE_A,), "a"),
    "s2": Link((fx.NOTE_A, fx.NOTE_B), "b"),
    "s3": Link((fx.NOTE_C,), "c"),
}
SPEND = {
    "s1": notes_cost.Spend(10.0, 1000),
    "s2": notes_cost.Spend(4.0, 400),
    "s3": notes_cost.Spend(5.0, 500),
}
WINDOW = (_ts("2026-10-15T00:00:00"), _ts("2026-10-25T00:00:00"))


def test_rows_split_session_spend_equally() -> None:
    rows = {r.id: r for r in notes.note_rows(NOTES, LINKS, SPEND)}
    assert rows[fx.NOTE_A].usd == 12.0
    assert rows[fx.NOTE_A].tokens == 1200
    assert rows[fx.NOTE_A].sessions == ["s1", "s2"]
    assert rows[fx.NOTE_B].usd == 2.0
    assert NOTE_E not in rows


def test_metrics_window_math() -> None:
    rows = notes.note_rows(NOTES, LINKS, SPEND)
    window_usd = {"s1": 10.0, "s2": 4.0, "s3": 5.0, "s4": 1.0}
    got = notes.metrics(NOTES, rows, WINDOW, window_usd, set(LINKS))
    # (A 12 + abandoned B 2) / done-and-linked {A}; E is done but unlinked.
    assert got == {
        "usd_per_note": 14.0,
        "note_linked_usd_share": 0.95,
        "notes_done": 2,
        "notes_done_linked": 1,
    }


def test_no_linked_done_note_leaves_usd_per_note_unmeasured() -> None:
    got = notes.metrics(NOTES[2:], [], WINDOW, {}, set())
    assert "usd_per_note" not in got
    assert got["note_linked_usd_share"] == 0.0
    assert got["notes_done"] == 1


def test_render_has_metrics_and_truncated_table() -> None:
    rows = notes.note_rows(NOTES, LINKS, SPEND)
    got = notes.metrics(NOTES, rows, WINDOW, {"s1": 1.0}, set(LINKS))
    text = "\n".join(notes.render(rows, got, {"a": 1, "c": 2}))
    assert "## Cost per todo note" in text
    assert "usd_per_note" in text
    assert "a=1" in text
    assert f"title of {fx.NOTE_A[:4]} " + "x" * 45 + "…" in text
    assert "| abandoned |" in text


def test_render_without_measurement_says_so() -> None:
    text = "\n".join(
        notes.render([], {"notes_done": 0, "note_linked_usd_share": 0.0}, {})
    )
    assert "usd_per_note: n/a" in text


def test_write_json_lists_every_linked_note(tmp_path: Path) -> None:
    rows = notes.note_rows(NOTES, LINKS, SPEND)
    path = notes.write_json(rows, tmp_path)
    data = json.loads(path.read_text())
    assert {r["id"] for r in data["notes"]} == {fx.NOTE_A, fx.NOTE_B, fx.NOTE_C}
    first = data["notes"][0]
    assert set(first) == {
        "id",
        "title",
        "status",
        "priority",
        "done_at",
        "sessions",
        "usd",
        "tokens",
    }
    assert first["usd"] == 12.0
