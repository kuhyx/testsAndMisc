"""Rule (d): an Implement/Continue handoff session inherits its writer's notes."""

from __future__ import annotations

from typing import TYPE_CHECKING

from python_pkg.token_audit import notes_backlog, notes_link, notes_scan
from python_pkg.token_audit.tests import test_notes_fixtures as fx

if TYPE_CHECKING:
    from pathlib import Path

HANDOFF = "/home/kuhy/.claude/handoff/sub/20261020-x.md"
HANDOFF2 = "/home/kuhy/.claude/handoff/20261021-y.md"


def _notes(tmp_path: Path) -> list[notes_backlog.Note]:
    return notes_backlog.parse_backlog(fx.backlog(tmp_path / "B.md").read_text())


def _writer(root: Path) -> None:
    fx.transcript(
        root,
        "w1",
        [
            fx.prompt(fx.BODY_A, "2026-10-20T08:00:00Z"),
            fx.tool_use(
                "Write",
                {"file_path": HANDOFF, "content": "x"},
                "2026-10-20T08:30:00Z",
            ),
        ],
    )


def test_continuation_inherits_writer_notes(tmp_path: Path) -> None:
    root = tmp_path / "projects"
    _writer(root)
    fx.transcript(
        root, "r1", [fx.prompt(f"Implement {HANDOFF}", "2026-10-20T09:00:00Z")]
    )
    links = notes_link.link_all(notes_scan.scan_root(root), _notes(tmp_path))
    assert links["w1"].rule == "c"
    assert links["r1"] == notes_link.Link((fx.NOTE_A,), "d")


def test_chain_follows_through_bash_heredoc_writer(tmp_path: Path) -> None:
    root = tmp_path / "projects"
    _writer(root)
    fx.transcript(
        root,
        "r1",
        [
            fx.prompt(f"Implement {HANDOFF}", "2026-10-20T09:00:00Z"),
            fx.tool_use(
                "Bash",
                {"command": "cat > ~/.claude/handoff/20261021-y.md <<'EOF'\nx\nEOF"},
                "2026-10-20T10:00:00Z",
            ),
        ],
    )
    fx.transcript(
        root, "r2", [fx.prompt(f"continue {HANDOFF2}", "2026-10-20T11:00:00Z")]
    )
    links = notes_link.link_all(notes_scan.scan_root(root), _notes(tmp_path))
    assert links["r2"] == notes_link.Link((fx.NOTE_A,), "d")


def test_subagent_writer_maps_to_parent(tmp_path: Path) -> None:
    root = tmp_path / "projects"
    fx.transcript(root, "w1", [fx.prompt(fx.BODY_B, "2026-10-20T08:00:00Z")])
    fx.subagent(
        root,
        "w1",
        "a1",
        [fx.tool_use("Write", {"file_path": HANDOFF}, "2026-10-20T08:10:00Z")],
    )
    fx.transcript(
        root, "r1", [fx.prompt(f"Implement {HANDOFF}", "2026-10-20T09:00:00Z")]
    )
    links = notes_link.link_all(notes_scan.scan_root(root), _notes(tmp_path))
    assert links["r1"] == notes_link.Link((fx.NOTE_B,), "d")


def test_appender_is_not_the_writer_and_unknown_handoff_unlinked(
    tmp_path: Path,
) -> None:
    root = tmp_path / "projects"
    fx.transcript(
        root,
        "x1",
        [
            fx.prompt(fx.BODY_B, "2026-10-20T07:00:00Z"),
            fx.tool_use(
                "Bash", {"command": f"cat >> {HANDOFF} <<'EOF'"}, "2026-10-20T07:10:00Z"
            ),
        ],
    )
    fx.transcript(
        root, "r1", [fx.prompt(f"Implement {HANDOFF}", "2026-10-20T09:00:00Z")]
    )
    assert "r1" not in notes_link.link_all(notes_scan.scan_root(root), _notes(tmp_path))


def test_write_after_reader_started_is_ignored(tmp_path: Path) -> None:
    root = tmp_path / "projects"
    fx.transcript(
        root, "r1", [fx.prompt(f"Implement {HANDOFF}", "2026-10-20T07:00:00Z")]
    )
    _writer(root)
    assert "r1" not in notes_link.link_all(notes_scan.scan_root(root), _notes(tmp_path))


def test_handoff_prompt_is_not_fuzzy_matched(tmp_path: Path) -> None:
    root = tmp_path / "projects"
    fx.transcript(
        root,
        "r1",
        [fx.prompt(f"Implement /home/kuhy/.claude/handoff/{fx.BODY_A.split()[0]}.md")],
    )
    assert notes_scan.scan_root(root)["r1"].handoff == f"{fx.BODY_A.split()[0]}.md"
    assert "r1" not in notes_link.link_all(notes_scan.scan_root(root), _notes(tmp_path))
