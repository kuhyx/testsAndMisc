from __future__ import annotations

import json
import os
from pathlib import Path

from python_pkg.token_audit import discover


def _touch(path: Path, mtime: float, text: str = "{}") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    os.utime(path, (mtime, mtime))
    return path


def test_find_transcripts_prunes_by_mtime_newest_first(tmp_path: Path) -> None:
    old = _touch(tmp_path / "p" / "old.jsonl", 1000)
    mid = _touch(tmp_path / "p" / "mid.jsonl", 20_000)
    new = _touch(tmp_path / "q" / "new.jsonl", 50_000)
    assert discover.find_transcripts(tmp_path, since=10_000) == [new, mid]
    assert discover.find_transcripts(tmp_path, since=0) == [new, mid, old]


def test_find_transcripts_includes_subagent_layout(tmp_path: Path) -> None:
    main = _touch(tmp_path / "p" / "s.jsonl", 100)
    sub = _touch(tmp_path / "p" / "s" / "subagents" / "agent-1.jsonl", 200)
    assert discover.find_transcripts(tmp_path, since=0) == [sub, main]


def test_first_cwd_skips_junk_and_cwdless_records(tmp_path: Path) -> None:
    lines = ["not json", "[1]", '{"a": 1}', '{"cwd": 5}', '{"cwd": "/x"}']
    path = _touch(tmp_path / "t.jsonl", 1, "\n".join(lines))
    assert discover.first_cwd(path) == "/x"


def test_first_cwd_none_when_absent(tmp_path: Path) -> None:
    path = _touch(tmp_path / "t.jsonl", 1, '{"a": 1}')
    assert discover.first_cwd(path) is None


def test_agent_meta_reads_sibling(tmp_path: Path) -> None:
    path = _touch(tmp_path / "agent-1.jsonl", 1)
    _touch(tmp_path / "agent-1.meta.json", 1, '{"agentType": "Explore"}')
    assert discover.agent_meta(path) == {"agentType": "Explore"}


def test_agent_meta_empty_when_missing_or_bad(tmp_path: Path) -> None:
    path = _touch(tmp_path / "agent-1.jsonl", 1)
    assert discover.agent_meta(path) == {}
    _touch(tmp_path / "agent-1.meta.json", 1, "garbage")
    assert discover.agent_meta(path) == {}


def _meta(path: Path, meta: dict[str, object] | str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = meta if isinstance(meta, str) else json.dumps(meta)
    path.write_text(text, encoding="utf-8")


def test_agent_meta_prefers_own_description(tmp_path: Path) -> None:
    own = tmp_path / "p" / "s" / "subagents" / "agent-1.meta.json"
    _meta(own, {"agentType": "Plan", "description": "mine"})
    _meta(
        tmp_path / "p" / "o" / "subagents" / "agent-1.meta.json", {"description": "x"}
    )
    path = own.parent / "agent-1.jsonl"
    assert discover.agent_meta(path) == {"agentType": "Plan", "description": "mine"}


def test_agent_meta_borrows_missing_fields(tmp_path: Path) -> None:
    sub = tmp_path / "p" / "new" / "subagents"
    _meta(sub / "agent-2.meta.json", {"agentType": "fork", "spawnDepth": 0})
    _meta(tmp_path / "p" / "bad" / "subagents" / "agent-2.meta.json", "not json")
    _meta(tmp_path / "p" / "nod" / "subagents" / "agent-2.meta.json", {"x": 1})
    _meta(
        tmp_path / "q" / "old" / "subagents" / "agent-2.meta.json",
        {"agentType": "general-purpose", "description": "spawned"},
    )
    assert discover.agent_meta(sub / "agent-2.jsonl") == {
        "agentType": "fork",
        "description": "spawned",
    }


def test_agent_meta_empty_when_nothing_found(tmp_path: Path) -> None:
    path = tmp_path / "p" / "s" / "subagents" / "agent-3.jsonl"
    path.parent.mkdir(parents=True)
    assert discover.agent_meta(path) == {}


def test_first_prompt_skips_non_prompts_and_truncates(tmp_path: Path) -> None:
    rows = [
        "junk",
        json.dumps({"type": "assistant", "message": {"content": "no"}}),
        json.dumps({"type": "user", "message": "flat"}),
        json.dumps({"type": "user", "message": {"content": 7}}),
        json.dumps(
            {"type": "user", "message": {"content": ["s", {"type": "tool_result"}]}}
        ),
        json.dumps({"type": "user", "message": {"content": "  \n"}}),
        json.dumps(
            {
                "type": "user",
                "message": {"content": [{"type": "text", "text": "x" * 80}]},
            }
        ),
    ]
    path = _touch(tmp_path / "t.jsonl", 1, "\n".join(rows))
    assert discover.first_prompt(path) == "x" * 59 + "…"
    assert discover.first_prompt(path, limit=100) == "x" * 80


def test_first_prompt_text_block_without_text(tmp_path: Path) -> None:
    row = {"type": "user", "message": {"content": [{"type": "text"}]}}
    path = _touch(tmp_path / "t.jsonl", 1, json.dumps(row))
    assert discover.first_prompt(path) == ""


def test_first_prompt_strips_harness_wrappers(tmp_path: Path) -> None:
    text = "<fork-boilerplate>\nYou are a fork <b>x</b>\n</fork-boilerplate>\nFix CI"
    row = {"type": "user", "message": {"content": text}}
    path = _touch(tmp_path / "t.jsonl", 1, json.dumps(row))
    assert discover.first_prompt(path) == "Fix CI"
