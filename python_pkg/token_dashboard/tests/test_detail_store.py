"""The detail tables are written per file, replaced on re-walk, filterable."""

from __future__ import annotations

from contextlib import closing
import sqlite3
from typing import TYPE_CHECKING

from python_pkg.token_dashboard import ingest
from python_pkg.token_dashboard.tests.conftest import (
    assistant,
    iso,
    prompt,
    result,
    use,
    write,
)

if TYPE_CHECKING:
    from pathlib import Path

COUNTS = (
    "SELECT (SELECT COUNT(*) FROM calls), (SELECT COUNT(*) FROM marks),"
    " (SELECT COUNT(*) FROM turn_detail)"
)


def _records(extra: int) -> list[dict[str, object]]:
    hook = {
        "type": "attachment",
        "timestamp": iso(1),
        "attachment": {"type": "hook_system_message", "hookName": "Stop"},
    }
    return [
        prompt("go", 0),
        hook,
        assistant("m1", 2, blocks=[use("t1", "Bash", command="ls")]),
        result("t1", 3),
        *[assistant(f"x{i}", 4 + i) for i in range(extra)],
    ]


def _ingest(tmp_path: Path) -> closing[sqlite3.Connection]:
    ingest.run(
        root=tmp_path / "projects",
        db_path=tmp_path / "t.sqlite",
        report_dir=tmp_path / "reports",
        budget_s=30.0,
    )
    return closing(sqlite3.connect(tmp_path / "t.sqlite"))


def test_rewalk_replaces_detail_rows(tmp_path: Path) -> None:
    path = tmp_path / "projects" / "proj" / "s1.jsonl"
    write(path, _records(1))
    with _ingest(tmp_path) as conn:
        assert conn.execute(COUNTS).fetchone() == (1, 1, 2)
    write(path, _records(2))
    with _ingest(tmp_path) as conn:
        assert conn.execute(COUNTS).fetchone() == (1, 1, 3)


def test_detail_rows_carry_the_shared_filter_columns(tmp_path: Path) -> None:
    write(tmp_path / "projects" / "proj" / "s1.jsonl", _records(1))
    with _ingest(tmp_path) as conn:
        call = conn.execute(
            "SELECT key, main_key, is_sub, cwd, model, day, family, target, batch,"
            " carry_calls FROM calls"
        ).fetchone()
        mark = conn.execute(
            "SELECT key, main_key, is_sub, cwd, model, kind, name, count FROM marks"
        ).fetchone()
        turn = conn.execute(
            "SELECT key, is_sub, cwd, model, latency_s FROM turn_detail ORDER BY ts"
        ).fetchone()
    assert call[:5] == ("s1", "s1", 0, "/repo", "claude-opus-5-5")
    assert call[6:] == ("ls", "ls", 1, 1)
    assert mark == ("s1", "s1", 0, "/repo", "claude-opus-5-5", "hook_msg", "Stop", 1)
    assert turn == ("s1", 0, "/repo", "claude-opus-5-5", 1.0)
