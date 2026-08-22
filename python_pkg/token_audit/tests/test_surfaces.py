"""Tests for the billed-surface enumerator."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from python_pkg.token_audit import surfaces


@pytest.fixture
def fake_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Build a minimal ~/.claude tree and point the module at it."""
    claude = tmp_path / ".claude"
    (claude / "rules").mkdir(parents=True)
    (claude / "rules" / "a.instructions.md").write_text("x" * 400)
    (claude / "memories").mkdir()
    (claude / "memories" / "m.md").write_text("y" * 200)
    (claude / "CLAUDE.md").write_text("z" * 100)
    memory = claude / "projects" / "-home-kuhy" / "memory"
    memory.mkdir(parents=True)
    (memory / "MEMORY.md").write_text("w" * 80)
    skill = claude / "skills" / "demo"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: demo\ndescription: hello there\n---\n")
    (claude / "settings.json").write_text(
        json.dumps(
            {
                "enabledPlugins": {"on@x": True, "off@y": False},
                "autoMode": {"environment": ["a", "b"]},
            }
        )
    )
    (tmp_path / ".claude.json").write_text(json.dumps({"mcpServers": {"aseprite": {}}}))
    (claude / "mcp-parked.json").write_text(json.dumps({"mcpServers": {"reaper": {}}}))
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".mcp.json").write_text(json.dumps({"mcpServers": {"local": {}}}))
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
    for name, value in [
        ("CLAUDE_DIR", claude),
        ("GLOBAL_CONFIG", tmp_path / ".claude.json"),
        ("SETTINGS", claude / "settings.json"),
    ]:
        monkeypatch.setattr(surfaces, name, value)
    return tmp_path


def test_every_surface_is_reported(fake_home: Path) -> None:
    """The enumeration is the contract: a missing row means a missed surface."""
    names = [s.name for s in surfaces.collect()]
    assert names == [
        "rules/",
        "memories/",
        "CLAUDE.md",
        "MEMORY.md",
        "skill descriptions",
        "plugins",
        "global MCP",
        "project .mcp.json",
        "autoMode.environment",
    ]


def test_sizes_come_from_disk(fake_home: Path) -> None:
    """Byte counts reflect real files."""
    found = {s.name: s for s in surfaces.collect()}
    assert found["rules/"].bytes_on_disk == 400
    assert found["rules/"].est_tokens == 100
    assert found["CLAUDE.md"].bytes_on_disk == 100
    assert found["MEMORY.md"].bytes_on_disk == 80


def test_enabled_plugins_only(fake_home: Path) -> None:
    """Disabled plugins cost nothing and must not be listed."""
    found = {s.name: s for s in surfaces.collect()}
    assert found["plugins"].detail == "on@x"
    assert found["plugins"].measurable


def test_mcp_split_between_active_and_parked(fake_home: Path) -> None:
    """Parked servers are reported separately from active ones."""
    found = {s.name: s for s in surfaces.collect()}
    assert found["global MCP"].detail == "1 active, 1 parked"


def test_project_mcp_files_counted(fake_home: Path) -> None:
    """Project-scoped configs are surfaced, not hidden."""
    found = {s.name: s for s in surfaces.collect()}
    assert "1 repos" in found["project .mcp.json"].detail


def test_skill_description_measured(fake_home: Path) -> None:
    """Skill frontmatter contributes bytes."""
    found = {s.name: s for s in surfaces.collect()}
    assert found["skill descriptions"].bytes_on_disk > 0
    assert "1 personal skills" in found["skill descriptions"].detail


def test_missing_files_are_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An absent tree or config contributes zero rather than raising."""
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
    for name in ("CLAUDE_DIR", "GLOBAL_CONFIG", "SETTINGS"):
        monkeypatch.setattr(surfaces, name, tmp_path / "nope")
    result = surfaces.collect()
    assert all(s.bytes_on_disk == 0 for s in result)
    assert surfaces._mcp_names(tmp_path / "nope.json") == []


def test_corrupt_json_is_tolerated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Malformed config files degrade to zero, never to a crash."""
    bad = tmp_path / "bad.json"
    bad.write_text("{oops")
    assert surfaces._json_field_bytes(bad, "autoMode") == 0
    assert surfaces._mcp_names(bad) == []
    monkeypatch.setattr(surfaces, "SETTINGS", bad)
    assert surfaces._enabled_plugins() == []


def test_absent_field_is_zero(tmp_path: Path) -> None:
    """A config without the field contributes nothing."""
    cfg = tmp_path / "s.json"
    cfg.write_text(json.dumps({"other": 1}))
    assert surfaces._json_field_bytes(cfg, "autoMode") == 0


def test_enabled_plugins_without_settings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No settings file means no plugins."""
    monkeypatch.setattr(surfaces, "SETTINGS", tmp_path / "gone.json")
    assert surfaces._enabled_plugins() == []


def test_tree_bytes_ignores_missing(tmp_path: Path) -> None:
    """A non-directory root totals zero."""
    assert surfaces._tree_bytes(tmp_path / "absent") == 0
