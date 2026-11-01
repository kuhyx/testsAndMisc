"""Rule (a): a Bash tool_use running note_claim.sh links the session."""

from __future__ import annotations

from typing import TYPE_CHECKING

from python_pkg.token_audit import notes_backlog, notes_link, notes_scan
from python_pkg.token_audit.tests import test_notes_fixtures as fx

if TYPE_CHECKING:
    from pathlib import Path


def _notes(tmp_path: Path) -> list[notes_backlog.Note]:
    return notes_backlog.parse_backlog(fx.backlog(tmp_path / "B.md").read_text())


def test_claim_with_prefix_links_note(tmp_path: Path) -> None:
    root = tmp_path / "projects"
    fx.transcript(
        root,
        "s1",
        [
            fx.prompt("do the thing"),
            fx.tool_use(
                "Bash", {"command": "~/.claude/scripts/note_claim.sh bbbbbbbb"}
            ),
        ],
    )
    links = notes_link.link_all(notes_scan.scan_root(root), _notes(tmp_path))
    assert links["s1"] == notes_link.Link((fx.NOTE_B,), "a")


def test_claim_beats_image_and_fuzzy(tmp_path: Path) -> None:
    root = tmp_path / "projects"
    fx.transcript(
        root,
        "s1",
        [
            fx.prompt(f"{fx.BODY_A}\n![x](todo-images/{fx.NOTE_C}/a.png)"),
            fx.tool_use("Bash", {"command": f"note_claim.sh {fx.NOTE_B}"}),
        ],
    )
    links = notes_link.link_all(notes_scan.scan_root(root), _notes(tmp_path))
    assert links["s1"].rule == "a"
    assert links["s1"].notes == (fx.NOTE_B,)


def test_unknown_or_ambiguous_claim_is_ignored(tmp_path: Path) -> None:
    root = tmp_path / "projects"
    fx.transcript(
        root,
        "s1",
        [
            fx.prompt("hello there general"),
            fx.tool_use("Bash", {"command": "note_claim.sh ffffffff"}),
        ],
    )
    notes = [
        *_notes(tmp_path),
        notes_backlog.Note("aaaaaaaa-9999", "dup", "dup", "low", "todo", None),
    ]
    facts = notes_scan.scan_root(root)
    assert "s1" not in notes_link.link_all(facts, notes)
    assert notes_link.resolve("aaaaaaaa", [n.id for n in notes]) is None


def test_claim_in_tool_result_is_not_a_link(tmp_path: Path) -> None:
    root = tmp_path / "projects"
    ids = f"{fx.NOTE_A} {fx.NOTE_B} {fx.NOTE_C}"
    fx.transcript(
        root,
        "s1",
        [
            fx.prompt("read my backlog please now"),
            fx.tool_use("Read", {"file_path": "/home/kuhy/src/todo/BACKLOG.md"}),
            fx.tool_result(f"note_claim.sh {fx.NOTE_A} {ids}"),
        ],
    )
    assert notes_link.link_all(notes_scan.scan_root(root), _notes(tmp_path)) == {}


def test_claim_inside_subagent_does_not_count(tmp_path: Path) -> None:
    root = tmp_path / "projects"
    fx.transcript(root, "s1", [fx.prompt("hello there general")])
    fx.subagent(
        root,
        "s1",
        "x",
        [fx.tool_use("Bash", {"command": f"note_claim.sh {fx.NOTE_A}"})],
    )
    assert notes_link.link_all(notes_scan.scan_root(root), _notes(tmp_path)) == {}
