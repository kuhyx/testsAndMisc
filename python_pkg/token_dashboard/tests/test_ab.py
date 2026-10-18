from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from python_pkg.token_dashboard import ab, ingest, schema
from python_pkg.token_dashboard.tests.conftest import (
    assistant,
    prompt,
    result,
    use,
    write,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_wilson_matches_reference_values() -> None:
    # Reference: Wilson score interval, z = 1.96 (Newcombe 1998, table I).
    low, high = ab.wilson(81, 263)
    assert (round(low, 4), round(high, 4)) == (0.2553, 0.3662)
    assert ab.wilson(0, 10)[0] == 0.0
    assert ab.wilson(0, 0) == (0.0, 1.0)


def test_newcombe_difference_contains_zero_for_equal_rates() -> None:
    diff, low, high = ab.diff_ci(5, 50, 5, 50)
    assert diff == 0.0
    assert low < 0 < high


def test_jaccard_and_correction_phrases() -> None:
    assert ab.jaccard("Find RTDB rules for tutor", "find rtdb rules tutor log") >= 0.6
    assert ab.jaccard("Find RTDB rules", "Write the README") == 0.0
    assert ab.is_correction("No, that's wrong")
    assert ab.is_correction("you missed the second file")
    assert not ab.is_correction("nothing else, thanks")


def _arm(n: int, redo: int, corr: int = 0) -> ab.ArmCounts:
    return ab.ArmCounts(n=n, redo=redo, correction=corr)


@pytest.mark.parametrize(
    ("sonnet", "opus", "level"),
    [
        (_arm(10, 9), _arm(10, 0), "grey"),
        (_arm(40, 20), _arm(40, 2), "red"),
        (_arm(40, 2, 20), _arm(40, 2, 1), "red"),
        (_arm(40, 6), _arm(40, 4), "green"),
        (_arm(40, 0), _arm(40, 20), "green"),  # Sonnet better is not a drop
    ],
)
def test_banner(sonnet: ab.ArmCounts, opus: ab.ArmCounts, level: str) -> None:
    found = ab.banner(sonnet, opus)
    assert found["level"] == level
    assert f"n={min(sonnet.n, opus.n)}" in found["text"] or level == "red"


def test_rebuild_joins_assignments_to_transcripts(tmp_path: Path) -> None:
    root = tmp_path / "projects"
    first = use("t1", "Agent", description="Review the parser change")
    again = use("t2", "Agent", description="Review the parser change again")
    msg = use("t3", "SendMessage", to="abc", message="more")
    write(
        root / "p" / "s1.jsonl",
        [
            prompt("go", 0),
            assistant("m1", 1, blocks=[first]),
            result("t1", 50, "done", toolUseResult={"agentId": "abc"}),
            assistant("m2", 60, blocks=[msg]),
            result("t3", 61),
            prompt("no, that's wrong", 100),
            assistant("m3", 101, blocks=[again]),
            result(
                "t2", 150, "err", toolUseResult={"agentId": "def", "status": "error"}
            ),
        ],
    )
    log = tmp_path / "agent-ab.jsonl"
    rows = [
        {"tool_use_id": "t1", "arm": "sonnet", "class": "review", "session_id": "s1"},
        {"tool_use_id": "t2", "arm": "opus", "class": "review", "session_id": "s1"},
    ]
    log.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    ingest.run(root, tmp_path / "t.sqlite", tmp_path / "report", 30.0)
    conn = schema.connect(tmp_path / "t.sqlite")
    payload = ab.rebuild(conn, log)
    stored = conn.execute(
        "SELECT tool_use_id, arm, key, main_key, is_sub, cwd, redo, followup,"
        " error, correction, tag FROM ab_rows ORDER BY tool_use_id"
    ).fetchall()
    payload = ab.rebuild(conn, log)  # a rebuild replaces, never appends
    count = conn.execute("SELECT COUNT(*) FROM ab_rows").fetchone()[0]
    conn.close()
    assert stored == [
        ("t1", "sonnet", "s1", "s1", 0, "/repo", 1, 1, 0, 1, "untagged"),
        ("t2", "opus", "s1", "s1", 0, "/repo", 0, 0, 1, 0, "untagged"),
    ]
    assert count == 2
    sonnet, opus = payload["arms"]["sonnet"], payload["arms"]["opus"]
    assert (sonnet["n"], opus["n"]) == (1, 1)
    assert sonnet["redo"]["k"] == 1
    assert sonnet["followup"]["k"] == 1
    assert sonnet["correction"]["k"] == 1
    assert opus["error"]["k"] == 1
    assert payload["banner"]["level"] == "grey"
