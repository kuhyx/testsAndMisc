"""Notes metrics wired into the audit CLI, and lifetime session pricing."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from python_pkg.token_audit import __main__ as cli
from python_pkg.token_audit import notes, notes_cost, pricing
from python_pkg.token_audit.tests import test_notes_fixtures as fx


def _session(root: Path) -> None:
    fx.transcript(
        root,
        "s1",
        [
            fx.prompt(fx.BODY_A),
            fx.tool_use("Bash", {"command": "ls"}, msg="m1"),
        ],
    )
    fx.subagent(root, "s1", "a1", [fx.tool_use("Read", {"file_path": "/x"}, msg="m2")])


def test_lifetime_spend_sums_main_and_subagents(tmp_path: Path) -> None:
    root = tmp_path / "projects"
    _session(root)
    book = pricing.load()
    got = notes_cost.lifetime({"s1": root / "proj" / "s1.jsonl"}, {"s1"}, book, {})
    assert got["s1"].tokens == 2000
    assert got["s1"].usd > 0
    reused = notes_cost.lifetime(
        {"s1": root / "proj" / "s1.jsonl"},
        {"s1"},
        book,
        {str(root / "proj" / "s1.jsonl"): notes_cost.Spend(1.0, 7)},
    )
    assert reused["s1"].tokens == 1007


def test_audit_writes_notes_section_and_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / "projects"
    _session(root)
    fx.backlog(notes.backlog_path_for(Path.home()))
    out = tmp_path / "out"
    code = cli.main(["--root", str(root), "--out", str(out), "--days", "36500"])
    assert code == 0
    assert "## Cost per todo note" in (out / "WEEKLY.md").read_text()
    snap = json.loads((out / "weekly.json").read_text())
    assert snap["metrics"]["notes_done"] == 2  # A and D (2026-09-01)
    assert snap["metrics"]["note_linked_usd_share"] == 1.0
    assert snap["metrics"]["usd_per_note"] > 0
    data = json.loads((out / "notes.json").read_text())
    assert data["notes"][0]["id"] == fx.NOTE_A
    assert "notes:" in capsys.readouterr().err


def test_audit_skips_notes_without_backlog(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / "projects"
    _session(root)
    out = tmp_path / "out"
    assert cli.main(["--root", str(root), "--out", str(out), "--days", "36500"]) == 0
    assert "notes: skipped" in capsys.readouterr().err
    assert not (out / "notes.json").exists()


def test_standalone_entry_writes_notes_json(tmp_path: Path) -> None:
    root = tmp_path / "projects"
    _session(root)
    fx.backlog(notes.backlog_path_for(Path.home()))
    out = tmp_path / "out"
    assert notes.main(["--root", str(root), "--out", str(out)]) == 0
    assert (out / "notes.json").exists()
    assert notes.main(["--root", str(tmp_path / "missing"), "--out", str(out)]) == 0
