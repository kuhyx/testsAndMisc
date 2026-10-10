from __future__ import annotations

import json
from pathlib import Path

from python_pkg.token_audit import parse
from python_pkg.token_audit.model import Turn


def _line(record: dict[str, object]) -> str:
    return json.dumps(record)


def test_tool_result_flushes_held_turn_in_order(tmp_path: Path) -> None:
    use = {"type": "tool_use", "id": "t1", "name": "Bash", "input": {}}
    records = [
        {
            "message": {
                "id": "m1",
                "model": "claude-opus-5",
                "usage": {"output_tokens": 2},
                "content": [use],
            },
        },
        {"message": {"content": [{"type": "tool_result", "tool_use_id": "t1"}]}},
    ]
    path = tmp_path / "s.jsonl"
    path.write_text("\n".join(_line(r) for r in records), encoding="utf-8")
    kinds = [kind for kind, _ in parse.iter_events(path)]
    assert kinds == ["turn", "tool"]


def test_load_session_tags_subagent(tmp_path: Path) -> None:
    sub = tmp_path / "proj" / "sess-1" / "subagents"
    sub.mkdir(parents=True)
    path = sub / "agent-a.jsonl"
    record = {"message": {"model": "claude-opus-5", "usage": {"output_tokens": 1}}}
    path.write_text(_line(record), encoding="utf-8")
    (sub / "agent-a.meta.json").write_text(
        json.dumps({"agentType": "Explore", "description": "find things"}),
        encoding="utf-8",
    )
    session = parse.load_session(path)
    assert session.parent_id == "sess-1"
    assert session.agent_type == "Explore"
    assert session.description == "find things"
    assert isinstance(session.turns[0], Turn)


def test_load_session_subagent_without_meta_defaults(tmp_path: Path) -> None:
    sub = tmp_path / "proj" / "sess-2" / "subagents"
    sub.mkdir(parents=True)
    path = sub / "agent-b.jsonl"
    path.write_text("{}", encoding="utf-8")
    session = parse.load_session(path)
    assert session.agent_type == "unknown"
    assert session.description == "(no label) agent-b"


def test_load_session_borrows_label_across_clear(tmp_path: Path) -> None:
    """An agent that outlived ``/clear`` keeps its spawning session's label."""
    old = tmp_path / "proj" / "old" / "subagents"
    new = tmp_path / "proj" / "new" / "subagents"
    old.mkdir(parents=True)
    new.mkdir(parents=True)
    (old / "agent-c.meta.json").write_text(
        json.dumps({"agentType": "Explore", "description": "map the repo"}),
        encoding="utf-8",
    )
    path = new / "agent-c.jsonl"
    path.write_text("{}", encoding="utf-8")
    session = parse.load_session(path)
    assert session.agent_type == "Explore"
    assert session.description == "map the repo"


def test_load_session_falls_back_to_first_prompt(tmp_path: Path) -> None:
    sub = tmp_path / "proj" / "sess-3" / "subagents"
    sub.mkdir(parents=True)
    path = sub / "agent-d.jsonl"
    prompt: dict[str, object] = {
        "type": "user",
        "message": {"content": "\nAudit the hooks\nmore"},
    }
    path.write_text(_line(prompt), encoding="utf-8")
    assert parse.load_session(path).description == "Audit the hooks"


def test_window_filters_records_by_timestamp(tmp_path: Path) -> None:
    def rec(stamp: str, mid: str) -> dict[str, object]:
        return {
            "timestamp": stamp,
            "message": {"id": mid, "usage": {"output_tokens": 1}},
        }

    path = tmp_path / "s.jsonl"
    rows = [
        rec("1970-01-01T00:00:10+00:00", "a"),
        rec("1970-01-01T00:01:40+00:00", "b"),
    ]
    path.write_text("\n".join(_line(r) for r in rows), encoding="utf-8")
    session = parse.load_session(path, (50.0, 200.0))
    assert [t.message_id for t in session.turns] == ["b"]
