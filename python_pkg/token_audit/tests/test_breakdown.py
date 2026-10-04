from __future__ import annotations

from pathlib import Path

import pytest

from python_pkg.token_audit import breakdown
from python_pkg.token_audit.model import Session, ToolCall, Turn
from python_pkg.token_audit.pricing import Price, PriceBook

BOOK = PriceBook(
    models={
        "claude-opus-5": Price(input=10.0, output=0.0, cache_read=0.0),
        "claude-sonnet-5-5": Price(input=2.0, output=0.0, cache_read=0.0),
    },
    default="claude-opus-5",
)
MILLION = 1_000_000


def _turn(
    model: str = "claude-opus-5",
    context: int = 0,
    stamp: float = 0.0,
    tokens: int = MILLION,
) -> Turn:
    return Turn(
        usage={"input_tokens": tokens},
        context=context,
        model=model,
        is_sidechain=False,
        timestamp=stamp,
    )


def _sessions() -> list[Session]:
    main = Session(
        "m",
        "m.jsonl",
        cwd=str(Path.home()),
        turns=[
            _turn(stamp=1000.0),
            _turn(context=breakdown.CONTEXT_BUDGET + 1, stamp=500.0),
            _turn(stamp=2000.0),
        ],
        tools=[ToolCall("Bash", 1, commit=True), ToolCall("Read", 1)],
    )
    sub_opus = Session(
        "a",
        "a.jsonl",
        cwd="/elsewhere",
        turns=[_turn()],
        parent_id="m",
        agent_type="Explore",
        description="scan",
    )
    sub_sonnet = Session(
        "b",
        "b.jsonl",
        turns=[_turn(model="claude-sonnet-5-5")],
        parent_id="m",
    )
    return [main, sub_opus, sub_sonnet]


def test_bucket_labels() -> None:
    assert breakdown._bucket(1) == "1-100"
    assert breakdown._bucket(100) == "1-100"
    assert breakdown._bucket(101) == "101-200"
    assert breakdown._bucket(1500) == "1001+"


def test_stamp_ignores_zero_and_tracks_span() -> None:
    found = breakdown.Breakdown()
    breakdown._stamp(found, 0.0)
    assert (found.earliest, found.latest) == (0.0, 0.0)
    breakdown._stamp(found, 100.0)
    breakdown._stamp(found, 50.0)
    assert (found.earliest, found.latest) == (50.0, 100.0)


def test_build_rolls_up_every_axis() -> None:
    found = breakdown.build(_sessions(), BOOK)
    assert found.usd_main == pytest.approx(30.0)
    assert found.usd_sub == pytest.approx(10.0 + 2.0)
    assert found.usd_total == pytest.approx(42.0)
    assert (found.calls_main, found.calls_sub, found.calls) == (3, 2, 5)
    assert found.over_budget_calls == 1
    assert found.over_budget_usd == pytest.approx(10.0)
    assert found.home_usd == pytest.approx(30.0)
    assert found.commits == 1
    assert found.by_agent_type == {"Explore": 10.0, "unknown": 2.0}
    assert found.by_description == {"scan": 10.0, "?": 2.0}
    assert found.sub_opus_usd == pytest.approx(10.0)
    assert found.sub_opus_repriced_usd == pytest.approx(2.0)
    assert found.buckets["1-100"].calls == 3
    assert (found.earliest, found.latest) == (500.0, 2000.0)


def test_days_has_one_minute_floor() -> None:
    assert breakdown.Breakdown().days == 60.0 / breakdown.SECONDS_PER_DAY


def test_metrics_for_populated_breakdown() -> None:
    m = breakdown.metrics(breakdown.build(_sessions(), BOOK))
    assert m["usd_total"] == 42.0
    assert m["calls"] == 5
    assert m["commits"] == 1
    assert m["usd_per_commit"] == 42.0
    assert m["usd_per_call"] == pytest.approx(8.4)
    assert m["subagent_usd_share"] == round(12 / 42, 4)
    assert m["subagent_opus_usd_share"] == round(10 / 12, 4)
    assert m["opus_usd_share"] == round(40 / 42, 4)
    assert m["home_cwd_usd_share"] == round(30 / 42, 4)
    assert m["over_budget_call_share"] == 0.2
    assert m["subagent_sonnet_saving_usd"] == 8.0


def test_metrics_for_empty_breakdown_is_all_zero() -> None:
    m = breakdown.metrics(breakdown.Breakdown())
    assert m["usd_per_call"] == 0.0
    assert m["usd_per_commit"] == 0.0
    assert m["subagent_usd_share"] == 0.0
    assert m["calls"] == 0


def test_render_has_every_section() -> None:
    text = "\n".join(breakdown.render(breakdown.build(_sessions(), BOOK)))
    for heading in (
        "## Dollar view",
        "### By model",
        "### Subagents by type",
        "### Costliest subagent tasks",
        "### Cost per call by position",
    ):
        assert heading in text
    assert "| claude-opus-5 | $40.00 |" in text
    assert "| 1-100 | $10.0000 | 3 |" in text
