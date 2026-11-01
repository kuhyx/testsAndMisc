"""The build-class A/B (agent-ab-build.jsonl) is summarised on its own."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from python_pkg.token_dashboard import ab, ingest, schema
from python_pkg.token_dashboard.tests.conftest import assistant, prompt, result, use
from python_pkg.token_dashboard.tests.conftest import write as write_jsonl

if TYPE_CHECKING:
    from pathlib import Path


def _store(tmp_path: Path) -> Path:
    root = tmp_path / "projects"
    write_jsonl(
        root / "p" / "s1.jsonl",
        [
            prompt("go", 0),
            assistant("m1", 1, blocks=[use("t1", "Agent", description="Build x")]),
            result("t1", 50, "done", toolUseResult={"agentId": "abc"}),
            assistant("m2", 60, blocks=[use("t2", "Agent", description="Review y")]),
            result("t2", 70, "done", toolUseResult={"agentId": "def"}),
        ],
    )
    db = tmp_path / "t.sqlite"
    ingest.run(root, db, tmp_path / "report", 30.0)
    return db


def _log(path: Path, rows: list[dict[str, str]]) -> Path:
    path.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    return path


def test_build_log_lands_in_its_own_meta_row(tmp_path: Path) -> None:
    conn = schema.connect(_store(tmp_path))
    judgment = _log(
        tmp_path / "agent-ab.jsonl",
        [{"tool_use_id": "t2", "arm": "opus", "class": "review"}],
    )
    build = _log(
        tmp_path / "agent-ab-build.jsonl",
        [{"tool_use_id": "t1", "arm": "sonnet", "class": "build"}],
    )
    ab.rebuild(conn, judgment, build)
    stored = {
        k: json.loads(v)
        for k, v in conn.execute("SELECT key, value FROM meta WHERE key LIKE 'ab%'")
    }
    rows = conn.execute("SELECT tool_use_id FROM ab_rows").fetchall()
    conn.close()
    assert stored["ab"]["arms"]["opus"]["n"] == 1
    assert stored["ab"]["arms"]["sonnet"]["n"] == 0
    assert stored["ab_build"]["arms"]["sonnet"]["n"] == 1
    assert stored["ab_build"]["arms"]["opus"]["n"] == 0
    assert stored["ab_build"]["banner"]["text"].startswith("A/B build agents")
    assert stored["ab"]["banner"]["text"].startswith("A/B judgment agents")
    assert rows == [("t2",)]


def test_missing_build_log_stores_an_empty_summary(tmp_path: Path) -> None:
    conn = schema.connect(_store(tmp_path))
    ab.rebuild(conn, tmp_path / "none.jsonl", tmp_path / "none-build.jsonl")
    raw = conn.execute("SELECT value FROM meta WHERE key = 'ab_build'").fetchone()
    conn.close()
    assert json.loads(raw[0])["arms"]["sonnet"]["n"] == 0
