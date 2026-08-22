"""Tests for the dual-window unused-surface detector."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from python_pkg.token_audit import unused


@pytest.fixture
def transcripts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect the transcript scan at a temporary tree."""
    root = tmp_path / "projects"
    (root / "proj").mkdir(parents=True)
    monkeypatch.setattr(unused, "TRANSCRIPT_ROOT", root)
    return root / "proj"


def test_dead_requires_both_windows_empty() -> None:
    """Used at 30 days but not 7 is not dead — the rule that prevents overreach."""
    assert unused.Usage("reaper", 0, 0).dead
    assert not unused.Usage("ck3", 0, 9).dead
    assert not unused.Usage("aseprite", 232, 748).dead


def test_usage_counts_across_windows(transcripts: Path) -> None:
    """A recent call lands in both windows; an old one only in the long window."""
    now = 1_000_000_000.0
    recent = transcripts / "recent.jsonl"
    recent.write_text('{"name":"mcp__aseprite__draw_line"}\n')
    import os

    os.utime(recent, (now - 3 * 86400, now - 3 * 86400))
    old = transcripts / "old.jsonl"
    old.write_text('{"name":"mcp__ck3__ck3_search"}\n')
    os.utime(old, (now - 20 * 86400, now - 20 * 86400))

    result = {
        u.name: u
        for u in unused.usage_for(
            ["aseprite", "ck3", "reaper"], unused._MCP_CALL, now=now
        )
    }
    assert result["aseprite"].short_calls == 1
    assert result["aseprite"].long_calls == 1
    assert result["ck3"].short_calls == 0
    assert result["ck3"].long_calls == 1
    assert result["reaper"].dead


def test_scan_skips_unreadable(
    transcripts: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unreadable transcript is skipped rather than aborting the audit."""
    bad = transcripts / "bad.jsonl"
    bad.write_text("{}")

    def boom(*_: object, **__: object) -> str:
        msg = "nope"
        raise OSError(msg)

    monkeypatch.setattr(Path, "read_text", boom)
    assert unused._scan(unused._MCP_CALL, 0) == {}


def test_mcp_usage_reads_config(tmp_path: Path, transcripts: Path) -> None:
    """Server names come from the global config."""
    cfg = tmp_path / "claude.json"
    cfg.write_text(json.dumps({"mcpServers": {"reaper": {}, "aseprite": {}}}))
    names = {u.name for u in unused.mcp_usage(cfg)}
    assert names == {"reaper", "aseprite"}


def test_mcp_usage_survives_bad_config(tmp_path: Path) -> None:
    """A corrupt config yields no rows instead of raising."""
    cfg = tmp_path / "broken.json"
    cfg.write_text("{not json")
    assert unused.mcp_usage(cfg) == []
    assert unused.mcp_usage(tmp_path / "missing.json") == []


def test_skill_usage_lists_installed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, transcripts: Path
) -> None:
    """Skill names come from the skills directory."""
    home = tmp_path / "home"
    skill = home / ".claude" / "skills" / "grilling"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: grilling\n---\n")
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    result = unused.skill_usage()
    assert [u.name for u in result] == ["grilling"]


def test_skill_pattern_matches_invocation() -> None:
    """The skill regex matches the transcript form."""
    assert unused._SKILL_CALL.findall('{"skill":"phone-deploy"}') == ["phone-deploy"]
