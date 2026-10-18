"""Edge cases of the walker, the summaries and the aux readers."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from python_pkg.token_dashboard import ab, context_files, finalize, ingest, schema, walk
from python_pkg.token_dashboard.tests.conftest import (
    assistant,
    prompt,
    result,
    use,
    write,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_timestampless_orphans_and_garbage_lines_are_tolerated(tmp_path: Path) -> None:
    path = tmp_path / "proj" / "s.jsonl"
    path.parent.mkdir()
    lines = ['{"type": "summary", "summary": "x"}', "{broken", ""]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    facts = walk.walk_file(path, tmp_path)
    assert facts.span == (0.0, 0.0)
    assert facts.rows.turns == []
    assert facts.final_tag is None


def test_a_result_without_its_call_is_ignored(tmp_path: Path) -> None:
    path = write(tmp_path / "proj" / "s.jsonl", [prompt("go", 0), result("nope", 1)])
    facts = walk.walk_file(path, tmp_path)
    assert facts.rows.tools == []


def test_a_nested_subagent_resolves_to_the_prompt_that_started_the_chain(
    tmp_path: Path,
) -> None:
    root = tmp_path / "projects"
    outer = use("ta", "Agent", description="outer")
    inner = use("tb", "Agent", description="inner")
    write(
        root / "p" / "s1.jsonl",
        [
            assistant("m0", 0),  # a turn before any prompt
            prompt("go", 5),
            assistant("m1", 10, blocks=[outer]),
            result("ta", 11, "ok", toolUseResult={"agentId": "aaa"}),
        ],
    )
    subs = root / "p" / "s1" / "subagents"
    write(
        subs / "agent-aaa.jsonl",
        [
            assistant("a1", 20, blocks=[inner]),
            result("tb", 21, toolUseResult={"agentId": "bbb"}),
        ],
    )
    write(subs / "agent-bbb.jsonl", [assistant("b1", 30)])
    ingest.run(root, tmp_path / "t.sqlite", tmp_path / "report", 30.0)
    conn = schema.connect(tmp_path / "t.sqlite")
    links = conn.execute(
        "SELECT sub_key, prompt_idx, depth FROM subagent_link ORDER BY depth"
    ).fetchall()
    first = conn.execute(
        "SELECT idx, text FROM prompt_summary WHERE key='s1' ORDER BY idx"
    ).fetchone()
    conn.close()
    assert links == [("s1/agent-aaa", 0, 1), ("s1/agent-bbb", 0, 2)]
    assert first == (-1, "(before the first prompt)")


def test_refreshing_an_unknown_session_changes_nothing(tmp_path: Path) -> None:
    conn = schema.connect(tmp_path / "t.sqlite")
    finalize.refresh(conn, "ghost")
    assert conn.execute("SELECT COUNT(*) FROM session_summary").fetchone() == (0,)
    conn.close()


def test_unreadable_prune_sizes_are_skipped(tmp_path: Path) -> None:
    claude, src = tmp_path / "claude", tmp_path / "src"
    prune = claude / "token-report" / "prune"
    for name, body in (
        ("a", "{broken"),
        ("b", "[1]"),
        ("c", '{"file_bytes": {"X.md": 9}}'),
    ):
        (prune / name).mkdir(parents=True)
        (prune / name / "sizes.json").write_text(body, encoding="utf-8")
    conn = schema.connect(tmp_path / "t.sqlite")
    context_files.refresh(conn, claude, src)
    sources = conn.execute("SELECT source FROM context_sizes").fetchall()
    conn.close()
    assert sources == [("prune c",)]


def test_unmatched_and_malformed_assignments_are_counted_unjoined(
    tmp_path: Path,
) -> None:
    log = tmp_path / "agent-ab.jsonl"
    rows = [
        {"tool_use_id": "ghost", "arm": "sonnet"},
        {"tool_use_id": "t1", "arm": "haiku"},
        {"tool_use_id": "t2"},
        [1],
    ]
    log.write_text("\n".join(json.dumps(r) for r in rows) + "\n{broken\n")
    conn = schema.connect(tmp_path / "t.sqlite")
    payload = ab.rebuild(conn, log)
    default = ab.rebuild(conn)  # the isolated, absent default log
    conn.close()
    assert payload["unjoined"] == 2
    assert payload["arms"]["sonnet"]["n"] == 0
    assert default["unjoined"] == 0
