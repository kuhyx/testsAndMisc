"""Rule (b): a typed user prompt naming todo-images/<uuid>/ links the note."""

from __future__ import annotations

from typing import TYPE_CHECKING

from python_pkg.token_audit import notes_backlog, notes_link, notes_scan
from python_pkg.token_audit.tests import test_notes_fixtures as fx

if TYPE_CHECKING:
    from pathlib import Path


def _notes(tmp_path: Path) -> list[notes_backlog.Note]:
    return notes_backlog.parse_backlog(fx.backlog(tmp_path / "B.md").read_text())


def test_image_path_in_later_prompt_links(tmp_path: Path) -> None:
    root = tmp_path / "projects"
    fx.transcript(
        root,
        "s1",
        [
            fx.prompt("something unrelated entirely here"),
            fx.prompt(f"see ~/data/todo-images/{fx.NOTE_C}/shot.png"),
        ],
    )
    links = notes_link.link_all(notes_scan.scan_root(root), _notes(tmp_path))
    assert links["s1"] == notes_link.Link((fx.NOTE_C,), "b")


def test_image_only_in_tool_result_does_not_link(tmp_path: Path) -> None:
    root = tmp_path / "projects"
    fx.transcript(
        root,
        "s1",
        [
            fx.prompt("something unrelated entirely here"),
            fx.tool_use("Bash", {"command": "ls"}),
            fx.tool_result(f"todo-images/{fx.NOTE_C}/shot.png"),
        ],
    )
    assert notes_link.link_all(notes_scan.scan_root(root), _notes(tmp_path)) == {}


def test_three_distinct_images_look_like_an_export(tmp_path: Path) -> None:
    root = tmp_path / "projects"
    refs = " ".join(f"todo-images/{n}/x.png" for n in (fx.NOTE_A, fx.NOTE_B, fx.NOTE_C))
    fx.transcript(root, "s1", [fx.prompt(f"zzz qqq www {refs}")])
    assert notes_link.link_all(notes_scan.scan_root(root), _notes(tmp_path)) == {}


def test_two_images_split_and_unknown_uuid_dropped(tmp_path: Path) -> None:
    root = tmp_path / "projects"
    unknown = "eeeeeeee-0000-4000-8000-000000000000"
    fx.transcript(
        root,
        "s1",
        [
            fx.prompt(
                f"zzz todo-images/{fx.NOTE_A}/x.png todo-images/{fx.NOTE_C}/y.png "
                f"todo-images/{unknown}/z.png"
            )
        ],
    )
    links = notes_link.link_all(notes_scan.scan_root(root), _notes(tmp_path))
    assert links["s1"] == notes_link.Link((fx.NOTE_A, fx.NOTE_C), "b")


def test_meta_and_sidechain_prompts_are_ignored(tmp_path: Path) -> None:
    root = tmp_path / "projects"
    meta = fx.prompt(f"todo-images/{fx.NOTE_C}/x.png") | {"isMeta": True}
    side = fx.prompt(f"todo-images/{fx.NOTE_C}/x.png") | {"isSidechain": True}
    fx.transcript(root, "s1", [meta, side, fx.prompt("plain words only here")])
    assert notes_link.link_all(notes_scan.scan_root(root), _notes(tmp_path)) == {}
