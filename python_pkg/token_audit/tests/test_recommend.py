from __future__ import annotations

from typing import Any

from python_pkg.token_audit import recommend


def _fire_all() -> dict[str, Any]:
    return {
        "usd_total": 70.0,
        "usd_per_day": 10.0,
        "subagent_usd_share": 0.4,
        "subagent_opus_usd_share": 0.9,
        "subagent_sonnet_saving_usd": 14.0,
        "over_budget_usd_share": 0.5,
        "home_cwd_usd_share": 0.4,
        "batching_calls_per_msg": 1.05,
        "bash_tokens_per_call": 900,
        "standing_tokens_est": 120,
        "image_usd_share": 0.1,
    }


def test_num_treats_missing_and_non_numeric_as_zero() -> None:
    assert recommend._num({"a": 3}, "a") == 3.0
    assert recommend._num({"a": "x"}, "a") == 0.0
    assert recommend._num({}, "a") == 0.0


def test_nothing_fires_on_quiet_metrics() -> None:
    assert recommend.candidates({}, None, [], []) == []
    assert recommend.render([]) == ["_No rule fired._"]


def test_subagent_rule_needs_both_thresholds() -> None:
    low_share = {"subagent_usd_share": 0.01, "subagent_opus_usd_share": 0.9}
    low_opus = {"subagent_usd_share": 0.5, "subagent_opus_usd_share": 0.1}
    assert recommend._subagents(low_share) == []
    assert recommend._subagents(low_opus) == []


def test_subagent_lever_sizes_saving_per_day() -> None:
    (lever,) = recommend._subagents(_fire_all())
    assert lever.category == "cheaper agents"
    # 70 / 10 = 7 days; 14 saved over 7 days = 2 per day.
    assert lever.est_usd_per_day == 2.0


def test_every_rule_fires_and_sized_levers_sort_first() -> None:
    previous = {"standing_tokens_est": 100}
    levers = recommend.candidates(_fire_all(), previous, ["mcp1"], ["skill1"])
    titles = [lv.title for lv in levers]
    assert titles[0] == "Calls over the context budget"
    assert set(titles) == {
        "Opus runs most subagent work",
        "Calls over the context budget",
        "Sessions started in ~",
        "Independent tool calls not batched",
        "Large Bash results",
        "Always-loaded context grew",
        "Images held in context",
        "Unused MCP servers / skills",
    }
    sized = [lv.est_usd_per_day for lv in levers if lv.est_usd_per_day]
    assert sized == sorted(sized, reverse=True)


def test_prefix_rule_silent_without_growth_or_baseline() -> None:
    flat = {"standing_tokens_est": 100}
    assert recommend._mechanics(flat, {"standing_tokens_est": 100}) == []
    assert recommend._mechanics(flat, {"standing_tokens_est": 0}) == []
    assert recommend._mechanics(flat, None) == []


def test_dead_lists_render_dash_for_empty_side() -> None:
    assert recommend._dead([], []) == []
    (only_mcp,) = recommend._dead(["m"], [])
    assert "MCP: m; skills: -" in only_mcp.evidence
    (only_skill,) = recommend._dead([], ["s"])
    assert "MCP: -; skills: s" in only_skill.evidence


def test_render_table_formats_estimates() -> None:
    sized = recommend.Lever("c", "t", "e", "a", 1.5)
    unsized = recommend.Lever("c", "t2", "e", "a")
    lines = recommend.render([sized, unsized])
    assert lines[0].startswith("| category")
    assert "| $1.50 |" in lines[2]
    assert "| - |" in lines[3]
