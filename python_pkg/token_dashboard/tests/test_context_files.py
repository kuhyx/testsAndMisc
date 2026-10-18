from __future__ import annotations

import json
import os
import subprocess
from typing import TYPE_CHECKING

from python_pkg.token_dashboard import context_files, gitcmd, schema

if TYPE_CHECKING:
    from pathlib import Path


def _tree(tmp_path: Path) -> tuple[Path, Path]:
    claude, src = tmp_path / ".claude", tmp_path / "src"
    for rel in (
        "CLAUDE.md",
        "rules/a.instructions.md",
        "rules/deep/b.md",
        "memories/mistakes.md",
        "skills/x/SKILL.md",
        "agents/reviewer.md",
        "projects/-home-kuhy/memory/MEMORY.md",
        "backups/rules-ondemand/not-loaded.md",
    ):
        (claude / rel).parent.mkdir(parents=True, exist_ok=True)
        (claude / rel).write_text("# x\n" * 10, encoding="utf-8")
    (src / "repo").mkdir(parents=True)
    (src / "repo" / "CLAUDE.md").write_text("## Commands\n", encoding="utf-8")
    (src / "repo" / "AGENTS.md").write_text("agents\n", encoding="utf-8")
    return claude, src


def test_enumerates_every_loaded_file_and_nothing_on_demand(tmp_path: Path) -> None:
    claude, src = _tree(tmp_path)
    found = {
        f.path.replace(str(tmp_path), ""): f for f in context_files.find(claude, src)
    }
    assert set(found) == {
        "/.claude/CLAUDE.md",
        "/.claude/rules/a.instructions.md",
        "/.claude/rules/deep/b.md",
        "/.claude/memories/mistakes.md",
        "/.claude/skills/x/SKILL.md",
        "/.claude/agents/reviewer.md",
        "/.claude/projects/-home-kuhy/memory/MEMORY.md",
        "/src/repo/CLAUDE.md",
        "/src/repo/AGENTS.md",
    }
    assert found["/.claude/rules/deep/b.md"].standing == "always"
    assert found["/src/repo/CLAUDE.md"].standing == "in repo"
    assert found["/.claude/skills/x/SKILL.md"].standing == "description"
    assert found["/.claude/projects/-home-kuhy/memory/MEMORY.md"].limit == 24_400


def _git(repo: Path, *args: str, when: int) -> None:
    env = {**os.environ, "GIT_AUTHOR_DATE": f"@{when} +0000"}
    env |= {"GIT_COMMITTER_DATE": f"@{when} +0000", "HOME": str(repo)}
    env |= {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t"}
    env |= {"GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    subprocess.run(
        [gitcmd.GIT, "-C", str(repo), *args], env=env, check=True, capture_output=True
    )


def test_size_history_from_git_and_prune_sizes(tmp_path: Path) -> None:
    claude, src = _tree(tmp_path)
    _git(claude, "init", "-q", when=1000)
    _git(claude, "add", "CLAUDE.md", when=1000)
    _git(claude, "commit", "-qm", "a", when=1000)
    (claude / "CLAUDE.md").write_text("longer\n" * 50, encoding="utf-8")
    _git(claude, "commit", "-qam", "b", when=2000)
    prune = claude / "token-report" / "prune" / "2026-10-12"
    prune.mkdir(parents=True)
    (prune / "sizes.json").write_text(json.dumps({"file_bytes": {"CLAUDE.md": 77}}))
    conn = schema.connect(tmp_path / "t.sqlite")
    context_files.refresh(conn, claude, src)
    rows = conn.execute(
        "SELECT ts, bytes, source FROM context_sizes WHERE path LIKE '%/CLAUDE.md'"
        " AND path NOT LIKE '%/src/%' ORDER BY ts"
    ).fetchall()
    listed = conn.execute("SELECT COUNT(*) FROM context_files").fetchone()[0]
    context_files.refresh(conn, claude, src)  # incremental: no duplicates
    again = conn.execute("SELECT COUNT(*) FROM context_sizes").fetchone()[0]
    conn.close()
    assert [(r[1], r[2]) for r in rows[:2]] == [(40, "git"), (350, "git")]
    assert (77, "prune 2026-10-12") in [(r[1], r[2]) for r in rows]
    assert listed == 9
    assert again == len(rows)


def test_price_mix_weights_cache_read_price_by_calls(tmp_path: Path) -> None:
    conn = schema.connect(tmp_path / "t.sqlite")
    rows = [
        ("claude-opus-5-5", 100.0),
        ("claude-opus-5-5", 101.0),
        ("claude-haiku-4-5", 102.0),
        ("claude-haiku-4-5", 1.0),
    ]
    conn.executemany("INSERT INTO turns (model, ts) VALUES (?, ?)", rows)
    price = context_files.price_mix(conn, now=200.0, days=150 / 86400)
    conn.close()
    assert round(price, 4) == round((0.2 * 2 + 0.1) / 3, 4)
