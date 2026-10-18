from __future__ import annotations

import json
from typing import TYPE_CHECKING

from python_pkg.token_dashboard import levers

if TYPE_CHECKING:
    from pathlib import Path

TABLE = """## Candidate levers (rule-based)

| category | lever | evidence | est $/day | action |
|---|---|---|---|---|
| cheaper agents | Opus runs most subagent work | subagents 64% | $14.47 | route |
| agent mechanics | Large Bash results | 40% of Bash | - | read ranges |

## Next
"""


def test_parse_candidate_table() -> None:
    rows = levers.parse_candidates(TABLE)
    assert [r["title"] for r in rows] == [
        "Opus runs most subagent work",
        "Large Bash results",
    ]
    assert rows[0]["est_usd_per_day"] == 14.47
    assert rows[1]["est_usd_per_day"] is None
    assert rows[0]["metric"] == "subagent_opus_usd_share"


def test_ledger_date_falls_back_to_text_then_unknown() -> None:
    assert levers.ledger_date({"date": "2026-10-04", "lever": "x"}) == "2026-10-04"
    assert levers.ledger_date({"lever": "weekly prefix prune 2026-10-05"}) == (
        "2026-10-05"
    )
    assert levers.ledger_date({"lever": "no date"}) is None


def _report(tmp_path: Path) -> Path:
    report = tmp_path / "report"
    (report / "history").mkdir(parents=True)
    ledger = [
        {
            "date": "2026-10-04",
            "lever": "routing",
            "metric": "subagent_opus_usd_share",
            "baseline": 0.98,
            "predicted": 0.55,
        },
        {
            "lever": "weekly prefix prune 2026-10-05",
            "metric": "standing_tokens_est",
            "baseline": 22187,
            "predicted": 19620,
        },
    ]
    (report / "ledger.jsonl").write_text(
        "\n".join(json.dumps(e) for e in ledger), encoding="utf-8"
    )
    for day, value in (("2026-10-10", 0.8), ("2026-10-17", 0.84)):
        snap = {
            "generated": f"{day}T10:00:00+00:00",
            "metrics": {"subagent_opus_usd_share": value, "standing_tokens_est": 23670},
        }
        (report / "history" / f"{day}.json").write_text(json.dumps(snap))
    for day in ("2026-10-05", "2026-10-12"):
        (report / "prune" / day).mkdir(parents=True)
        (report / "prune" / day / "PROPOSAL.md").write_text(
            f"# Prefix prune proposal {day}\n\nModest week. Estimated ~ -0.35k.\n"
        )
    return report


def test_build_rows_status_and_outcome(tmp_path: Path) -> None:
    report = _report(tmp_path)
    tables = {"2026-10-10": TABLE}
    rows = levers.build(report, tables)
    applied = [r for r in rows if r["source"] == "ledger"]
    assert [r["lever"] for r in applied] == [
        "routing",
        "weekly prefix prune 2026-10-05",
    ]
    assert applied[0]["outcome"] == "helped"
    assert applied[1]["outcome"] == "regressed"
    assert applied[1]["date"] == "2026-10-05"
    status = {r["source"]: r["status"] for r in rows if r["source"].startswith("prune")}
    assert status == {"prune 2026-10-05": "applied", "prune 2026-10-12": "proposed"}
    # The 10-10 Opus candidate was followed by no ledger line on its metric
    # and a newer snapshot exists, so it was not applied.
    opus = next(r for r in rows if r["lever"] == "Opus runs most subagent work")
    assert opus["status"] == "not applied"


def test_structured_levers_in_a_snapshot_win_over_markdown(tmp_path: Path) -> None:
    report = _report(tmp_path)
    snap_path = report / "history" / "2026-10-17.json"
    snap = json.loads(snap_path.read_text())
    snap["levers"] = [
        {
            "category": "c",
            "title": "Structured one",
            "evidence": "e",
            "action": "a",
            "est_usd_per_day": 1.5,
            "metric": "usd_per_day",
        },
    ]
    snap_path.write_text(json.dumps(snap))
    rows = levers.build(report, {})
    found = next(r for r in rows if r["lever"] == "Structured one")
    assert found["status"] == "proposed"
    assert found["source"] == "snapshot 2026-10-17"
