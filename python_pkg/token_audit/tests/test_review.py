from __future__ import annotations

from typing import Any

import pytest

from python_pkg.token_audit import attribute, history, review, surfaces, unused
from python_pkg.token_audit.model import Session, ToolCall, Turn


def _usage(name: str, short: int, long: int) -> unused.Usage:
    return unused.Usage(name, short, long)


def _axes(*, bash: bool, spend: bool) -> tuple[attribute.Totals, attribute.Axes]:
    usage = {"output_tokens": 10} if spend else {}
    turn = Turn(usage=usage, context=0, model="claude-opus-5", is_sidechain=False)
    tools = [ToolCall("Bash", 400)] if bash else []
    return attribute.build([Session("s", "s.jsonl", turns=[turn], tools=tools)])


def test_extra_metrics_with_bash_and_spend(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = [surfaces.Surface("a", "d", 40), surfaces.Surface("b", "d", 80)]
    monkeypatch.setattr(review.surfaces, "collect", lambda: fake)
    totals, axes = _axes(bash=True, spend=True)
    axes.image_cost = totals.weighted / 2
    m = review.extra_metrics(totals, axes)
    assert m["bash_tokens_per_call"] > 0
    assert m["image_usd_share"] == 0.5
    assert m["standing_tokens_est"] == 30
    assert "batching_calls_per_msg" in m


def test_extra_metrics_without_bash_or_spend() -> None:
    totals, axes = _axes(bash=False, spend=False)
    m = review.extra_metrics(totals, axes)
    assert m["bash_tokens_per_call"] == 0.0
    assert m["image_usd_share"] == 0.0


def test_comparison_without_usable_previous() -> None:
    assert "No comparable previous snapshot" in review._comparison({}, None)[0]
    assert "No comparable previous snapshot" in review._comparison({}, {"v": 1})[0]
    assert "No comparable previous snapshot" in review._comparison({}, {})[0]


def test_comparison_table_rows() -> None:
    prev: dict[str, Any] = {
        "v": review.SNAPSHOT_VERSION,
        "metrics": {
            "usd_per_day": 100.0,
            "usd_per_call": 0,
            "calls_per_day": "bad",
            "usd_per_commit": 2.0,
        },
    }
    now = {"usd_per_day": 50.0, "usd_per_call": 1.0, "calls_per_day": 3.0}
    rows = review._comparison(now, prev)
    assert rows[0].startswith("| metric")
    assert "| usd_per_day | 100.0 | 50.0 | -50.0% |" in rows
    assert "| usd_per_call | 0 | 1.0 | n/a |" in rows
    assert len(rows) == 4  # header, rule, two rendered metrics


def test_ledger_empty_and_populated() -> None:
    assert review._ledger({"metrics": {}}) == ["_Ledger empty: nothing applied yet._"]
    history.append_ledger(
        {"lever": "L1", "metric": "m", "baseline": 10, "predicted": 5}
    )
    history.append_ledger({"lever": "L2", "metric": "gone", "baseline": 1})
    lines = review._ledger({"metrics": {"m": 4}})
    text = "\n".join(lines)
    assert "| L1 | m | 10.0 | 5.0 | 4.0 | **helped** |" in text
    assert "| L2 | gone | 1.0 | - | - | **unmeasured** |" in text


def _patch_dead(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        review.unused,
        "mcp_usage",
        lambda: [_usage("deadmcp", 0, 0), _usage("live", 1, 0)],
    )
    monkeypatch.setattr(
        review.unused, "skill_usage", lambda: [_usage("deadskill", 0, 0)]
    )


def test_render_without_levers_has_no_candidates() -> None:
    snap = {"metrics": {"usd_per_day": 1.0}}
    text = "\n".join(review.render(snap, None, levers=False))
    assert "## Since the previous analysis" in text
    assert "## What helped (ledger)" in text
    assert "Candidate levers" not in text


def test_render_with_levers_uses_previous_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_dead(monkeypatch)
    snap = {"metrics": {"standing_tokens_est": 200}}
    prev = {"v": review.SNAPSHOT_VERSION, "metrics": {"standing_tokens_est": 100}}
    text = "\n".join(review.render(snap, prev, levers=True))
    assert "## Candidate levers (rule-based)" in text
    assert "Always-loaded context grew" in text
    assert "MCP: deadmcp; skills: deadskill" in text


def test_render_with_levers_ignores_old_or_missing_previous(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_dead(monkeypatch)
    snap = {"metrics": {"standing_tokens_est": 200}}
    for prev in (None, {"v": 1, "metrics": {"standing_tokens_est": 100}}):
        text = "\n".join(review.render(snap, prev, levers=True))
        assert "Always-loaded context grew" not in text
