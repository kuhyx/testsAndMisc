from __future__ import annotations

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
