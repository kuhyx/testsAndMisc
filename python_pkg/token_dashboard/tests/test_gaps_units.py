"""Edge cases of the small pure helpers: blocks, gitcmd, levers, schema, efficiency."""

from __future__ import annotations

import json
import sqlite3
import subprocess
from typing import TYPE_CHECKING

import pytest

from python_pkg.token_dashboard import blocks, efficiency, gitcmd, levers, schema

if TYPE_CHECKING:
    from pathlib import Path


def test_text_of_joins_text_blocks_and_ignores_the_rest() -> None:
    content = [
        {"type": "text", "text": "one"},
        {"type": "image"},
        "stray",
        {"type": "text", "text": "two"},
    ]
    assert blocks.text_of(content) == "one\ntwo"
    assert blocks.text_of("plain") == "plain"
    assert blocks.text_of(None) == ""
    assert blocks.text_of({"type": "text", "text": "dict"}) == ""


def test_compact_summaries_and_tool_results_are_not_prompts() -> None:
    message = {"role": "user", "content": "summary of the chat"}
    summary = {"type": "user", "isCompactSummary": True, "message": message}
    assert blocks.prompt_text(summary) is None
    visible = {"type": "user", "isVisibleInTranscriptOnly": True, "message": message}
    assert blocks.prompt_text(visible) is None
    tool = [{"type": "tool_result", "tool_use_id": "t", "content": "x"}]
    reply = {"type": "user", "message": {"content": tool}}
    assert blocks.prompt_text(reply) is None


def test_repo_hint_falls_back_to_cwd_and_resolves_relative_targets() -> None:
    assert blocks.repo_hint("git commit -m x", None) == ""
    assert blocks.repo_hint("git commit -m x", "/work/r") == "/work/r"
    assert blocks.repo_hint("cd sub && git commit", "/work/r") == "/work/r/sub"
    assert blocks.repo_hint("git -C /abs/repo commit", "/work/r") == "/abs/repo"


def test_lever_table_needs_the_heading_and_at_least_one_row() -> None:
    heading = f"## {blocks.LEVER_HEADING}\n\n"
    assert blocks.lever_table("nothing here") is None
    assert blocks.lever_table(heading + "just prose") is None
    assert (
        blocks.lever_table(heading + "| a | b |\n| c | d |") == "| a | b |\n| c | d |"
    )


@pytest.mark.parametrize(
    "error", [OSError("no git"), subprocess.TimeoutExpired("git", 1)]
)
def test_git_run_never_raises(
    error: Exception, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def boom(*_args: object, **_kwargs: object) -> None:
        raise error

    monkeypatch.setattr("python_pkg.token_dashboard.gitcmd.subprocess.run", boom)
    assert gitcmd.run(tmp_path, "status") is None


def test_unreadable_or_non_object_snapshots_are_skipped(tmp_path: Path) -> None:
    history = tmp_path / "history"
    history.mkdir()
    (history / "2026-10-01.json").write_text("{broken")
    (history / "2026-10-02.json").write_text(json.dumps([1, 2]))
    (history / "2026-10-03.json").write_text(json.dumps({"metrics": {}}))
    assert levers._snapshots(tmp_path) == [("2026-10-03", {"metrics": {}})]


def test_readonly_store_refuses_writes(tmp_path: Path) -> None:
    db = tmp_path / "t.sqlite"
    schema.connect(db).close()
    conn = schema.connect(db, readonly=True)
    try:
        assert conn.execute("SELECT COUNT(*) FROM turns").fetchone() == (0,)
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            conn.execute("INSERT INTO meta VALUES ('k', 'v')")
    finally:
        conn.close()


def test_commits_with_an_unrecognised_verdict_count_as_unknown() -> None:
    (week,) = efficiency.commits_weekly([(1.0, "mystery")], {})
    assert (week["unknown"], week["survived"], week["lost"]) == (1, 0, 0)
