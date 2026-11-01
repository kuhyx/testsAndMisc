"""Edge cases of the note join that the rule tests do not reach."""

from __future__ import annotations

from pathlib import Path

from python_pkg.token_audit import (
    notes,
    notes_backlog,
    notes_collect,
    notes_link,
    notes_scan,
    pricing,
)
from python_pkg.token_audit.model import Session
from python_pkg.token_audit.tests import test_notes_fixtures as fx

HANDOFF = "/home/kuhy/.claude/handoff/e.md"


def test_prompt_text_rejects_tool_results_and_non_text() -> None:
    result = fx.tool_result("x")
    assert notes_scan.prompt_text(result) is None
    empty = fx.prompt("x")
    empty["message"]["content"] = None
    assert notes_scan.prompt_text(empty) is None


def test_bad_backlog_stamp_and_malformed_status_field() -> None:
    text = '<!-- @note id="x" updated="garbage" -->\nbody'
    assert notes_backlog.parse_backlog(text)[0].updated is None
    odd = '{"n": {"fields": {"status": [2]}}}'
    assert notes_backlog.merge_devices({"d": odd}) == {}


def test_non_handoff_writes_and_repeat_writes_are_ignored(tmp_path: Path) -> None:
    root = tmp_path / "projects"
    fx.transcript(
        root,
        "w1",
        [
            fx.tool_use("Write", {"file_path": "/home/kuhy/notes/x.md"}, msg="m1"),
            fx.tool_use("Write", {"file_path": HANDOFF}, "2026-10-20T09:00:00Z", "m2"),
            fx.tool_use("Write", {"file_path": HANDOFF}, "2026-10-20T10:00:00Z", "m3"),
        ],
    )
    fx.subagent(root, "orphan", "z", [fx.tool_use("Write", {"file_path": HANDOFF})])
    facts = notes_scan.scan_root(root)
    assert set(facts) == {"w1"}
    assert list(facts["w1"].creates) == ["e.md"]


def test_unlinked_writer_passes_nothing_on(tmp_path: Path) -> None:
    root = tmp_path / "projects"
    fx.transcript(
        root,
        "w1",
        [
            fx.prompt("nothing matching at all here", "2026-10-20T08:00:00Z"),
            fx.tool_use("Write", {"file_path": HANDOFF}, "2026-10-20T08:10:00Z"),
        ],
    )
    fx.transcript(
        root, "r1", [fx.prompt(f"Implement {HANDOFF}", "2026-10-20T09:00:00Z")]
    )
    notes_list = notes_backlog.parse_backlog(fx.backlog(tmp_path / "B.md").read_text())
    assert notes_link.link_all(notes_scan.scan_root(root), notes_list) == {}


def test_sessions_started_before_window_are_not_reused(tmp_path: Path) -> None:
    root = tmp_path / "projects"
    path = fx.transcript(root, "s1", [fx.prompt("x", "2026-10-01T00:00:00Z")])
    facts = notes_scan.scan_root(root)
    sessions = [Session("s1", str(path)), Session("ghost", "/nowhere")]
    reuse = notes_collect._reusable(sessions, facts, 2e9, pricing.load())
    assert reuse == {}


def test_standalone_entry_without_backlog_writes_nothing(tmp_path: Path) -> None:
    out = tmp_path / "out"
    assert notes.main(["--root", str(tmp_path), "--out", str(out)]) == 0
    assert not out.exists()
