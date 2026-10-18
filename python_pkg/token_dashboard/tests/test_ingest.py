from __future__ import annotations

import json
import sqlite3
from typing import TYPE_CHECKING

import pytest

from python_pkg.token_dashboard import ingest
from python_pkg.token_dashboard.tests.conftest import (
    assistant,
    prompt,
    result,
    usd_opus_output,
    use,
    write,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from pathlib import Path


def _tree(root: Path) -> None:
    agent = use("ta", "Agent", description="Find x", subagent_type="Explore")
    write(
        root / "proj" / "s1.jsonl",
        [
            prompt("first", 0),
            assistant("m1", 10, blocks=[agent]),
            result("ta", 11, "launched", toolUseResult={"agentId": "abc"}),
            assistant("m2", 20),
            prompt("second", 1000),
            assistant("m3", 1010, blocks=[{"type": "text", "text": "DONE: x"}]),
        ],
    )
    subdir = root / "proj" / "s1" / "subagents"
    write(subdir / "agent-abc.jsonl", [prompt("task", 12), assistant("a1", 200)])
    (subdir / "agent-abc.meta.json").write_text(
        json.dumps({"agentType": "Explore", "description": "Find x"}),
        encoding="utf-8",
    )
    # An agent that outlived /clear: nothing in s1 spawned it.
    write(subdir / "agent-zzz.jsonl", [prompt("orphan", 30), assistant("z1", 40)])


def _run(tmp_path: Path, budget: float = 30.0) -> ingest.Outcome:
    return ingest.run(
        root=tmp_path / "projects",
        db_path=tmp_path / "t.sqlite",
        report_dir=tmp_path / "report",
        budget_s=budget,
    )


@pytest.fixture
def db(tmp_path: Path) -> Iterator[Callable[[], sqlite3.Connection]]:
    opened: list[sqlite3.Connection] = []

    def _open() -> sqlite3.Connection:
        opened.append(sqlite3.connect(tmp_path / "t.sqlite"))
        return opened[-1]

    yield _open
    for conn in opened:
        conn.close()


def test_session_cost_reconciles_to_prompts_plus_unattributed(
    tmp_path: Path, db: Callable[[], sqlite3.Connection]
) -> None:
    _tree(tmp_path / "projects")
    outcome = _run(tmp_path)
    assert outcome.complete
    conn = db()
    usd, active_s, wall_s, tag = conn.execute(
        "SELECT usd, active_s, wall_s, final_tag FROM session_summary WHERE key='s1'"
    ).fetchone()
    assert usd == pytest.approx(usd_opus_output(1000) * 5)
    prompts = conn.execute(
        "SELECT idx, usd_own + usd_sub FROM prompt_summary WHERE key='s1' ORDER BY idx"
    ).fetchall()
    unattributed = conn.execute(
        "SELECT SUM(usd) FROM subagent_link WHERE main_key='s1' AND prompt_idx IS NULL"
    ).fetchone()[0]
    assert sum(v for _, v in prompts) + unattributed == pytest.approx(usd)
    # Prompt 0 carries its own two turns plus the Explore agent it spawned.
    assert prompts[0][1] == pytest.approx(usd_opus_output(1000) * 3)
    assert wall_s == 1010
    # Union of main + subagent activity: 0..200 bridged, then 1000..1010.
    assert active_s == pytest.approx(210)
    assert tag == "DONE"


def test_subagent_links_to_its_prompt_via_agent_id(
    tmp_path: Path, db: Callable[[], sqlite3.Connection]
) -> None:
    _tree(tmp_path / "projects")
    _run(tmp_path)
    rows = dict(
        db().execute("SELECT sub_key, prompt_idx FROM subagent_link").fetchall()
    )
    assert rows == {"s1/agent-abc": 0, "s1/agent-zzz": None}


def test_rerun_skips_unchanged_and_rows_outlive_deleted_files(
    tmp_path: Path, db: Callable[[], sqlite3.Connection]
) -> None:
    _tree(tmp_path / "projects")
    _run(tmp_path)
    assert _run(tmp_path).parsed == 0
    (tmp_path / "projects" / "proj" / "s1.jsonl").unlink()
    _run(tmp_path)
    count = db().execute("SELECT COUNT(*) FROM turns").fetchone()[0]
    assert count == 5


def test_changed_file_is_reparsed_without_duplicating_rows(
    tmp_path: Path, db: Callable[[], sqlite3.Connection]
) -> None:
    _tree(tmp_path / "projects")
    _run(tmp_path)
    path = tmp_path / "projects" / "proj" / "s1.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(assistant("m4", 1020)) + "\n")
    assert _run(tmp_path).parsed == 1
    count = db().execute("SELECT COUNT(*) FROM turns").fetchone()[0]
    assert count == 6


def test_zero_budget_leaves_work_pending_and_resumes(tmp_path: Path) -> None:
    _tree(tmp_path / "projects")
    first = _run(tmp_path, budget=0.0)
    assert not first.complete
    assert first.parsed == 1  # always makes progress
    rest = _run(tmp_path)
    assert rest.complete
    assert first.parsed + rest.parsed == 3


def test_daily_rollup_matches_turns(
    tmp_path: Path, db: Callable[[], sqlite3.Connection]
) -> None:
    _tree(tmp_path / "projects")
    _run(tmp_path)
    conn = db()
    total, calls, sub = conn.execute(
        "SELECT SUM(usd), SUM(calls), SUM(usd_sub) FROM daily"
    ).fetchone()
    assert total == pytest.approx(usd_opus_output(1000) * 5)
    assert calls == 5
    assert sub == pytest.approx(usd_opus_output(1000) * 2)


def test_cli_exit_codes(tmp_path: Path) -> None:
    _tree(tmp_path / "projects")
    args = [
        "--root",
        str(tmp_path / "projects"),
        "--db",
        str(tmp_path / "t.sqlite"),
        "--report-dir",
        str(tmp_path / "report"),
    ]
    assert ingest.main([*args, "--budget", "0"]) == ingest.EXIT_PENDING
    assert ingest.main(args) == 0


def test_session_with_no_prompts_and_no_main_file(
    tmp_path: Path, db: Callable[[], sqlite3.Connection]
) -> None:
    sub = tmp_path / "projects" / "proj" / "gone" / "subagents" / "agent-q.jsonl"
    write(sub, [assistant("q1", 5), assistant("q2", 6)])
    assert _run(tmp_path).complete
    usd, prompts = (
        db()
        .execute("SELECT usd, prompts FROM session_summary WHERE key='gone'")
        .fetchone()
    )
    assert usd == pytest.approx(usd_opus_output(1000) * 2)
    assert prompts == 0
