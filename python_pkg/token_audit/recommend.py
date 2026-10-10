"""Deterministic lever candidates: thresholds in code, not in a model's head.

Every rule reads the snapshot ``metrics`` (and the previous snapshot's, for
growth checks) and either emits a :class:`Lever` or stays silent. The skill
layered on top adds judgment -- which levers suit the user, how to phrase a
prompt habit -- but never decides *whether* a number crossed a line; that is
an ``if`` statement and lives here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Rule thresholds. Each is the point past which the lever is worth a look,
# chosen from the 2026-10-04 audit's distributions, not tuned to fire.
SUBAGENT_SHARE = 0.15
SUBAGENT_OPUS_SHARE = 0.5
OVER_BUDGET_SHARE = 0.2
HOME_CWD_SHARE = 0.2
BATCHING_MIN = 1.15
BASH_BIG_SHARE = 0.25
PREFIX_GROWTH = 0.05
IMAGE_SHARE = 0.03


@dataclass(frozen=True)
class Lever:
    """One candidate change, sized where the data allows."""

    category: str
    title: str
    evidence: str
    action: str
    est_usd_per_day: float | None = None


def _num(metrics: dict[str, Any], key: str) -> float:
    """Read a numeric metric, treating anything missing as zero."""
    value = metrics.get(key, 0)
    return float(value) if isinstance(value, (int, float)) else 0.0


def _subagents(m: dict[str, Any]) -> list[Lever]:
    """Opus doing mechanical subagent work."""
    if _num(m, "subagent_usd_share") < SUBAGENT_SHARE:
        return []
    if _num(m, "subagent_opus_usd_share") < SUBAGENT_OPUS_SHARE:
        return []
    saving = _num(m, "subagent_sonnet_saving_usd")
    days = _num(m, "usd_total") / max(_num(m, "usd_per_day"), 1e-9)
    return [
        Lever(
            "cheaper agents",
            "Opus runs most subagent work",
            f"subagents {_num(m, 'subagent_usd_share'):.0%} of spend, "
            f"{_num(m, 'subagent_opus_usd_share'):.0%} of that on Opus; "
            f"re-priced at Sonnet the same turns cost ${saving:,.2f} less",
            "route coverage/test/search agents to the Sonnet-pinned agent "
            "definitions; keep implementers on the default",
            saving / days if days else None,
        ),
    ]


def _shape(m: dict[str, Any]) -> list[Lever]:
    """Session shape: context budget and working directory."""
    out: list[Lever] = []
    per_day = _num(m, "usd_per_day")
    if _num(m, "over_budget_usd_share") > OVER_BUDGET_SHARE:
        out.append(
            Lever(
                "session length",
                "Calls over the context budget",
                f"{_num(m, 'over_budget_usd_share'):.0%} of spend ran with "
                "context above the gate's budget",
                "check the context gate fires (hook log) and that handoffs are "
                "being written; lower the budget if they are",
                # Calls over budget cost ~2.4x a fresh call (21k vs 51k).
                per_day * _num(m, "over_budget_usd_share") * 0.58,
            ),
        )
    if _num(m, "home_cwd_usd_share") > HOME_CWD_SHARE:
        out.append(
            Lever(
                "prompt habits",
                "Sessions started in ~",
                f"{_num(m, 'home_cwd_usd_share'):.0%} of spend had cwd=~ "
                "(no repo CLAUDE.md, so agents explore to find commands)",
                "start claude inside the repo; add exact run/test commands to "
                "each repo's CLAUDE.md",
            ),
        )
    return out


def _mechanics(m: dict[str, Any], prev: dict[str, Any] | None) -> list[Lever]:
    """Batching, output size, prefix growth, images."""
    out: list[Lever] = []
    ratio = _num(m, "batching_calls_per_msg")
    if 0 < ratio < BATCHING_MIN:
        out.append(
            Lever(
                "agent mechanics",
                "Independent tool calls not batched",
                f"{ratio:.2f} calls per tool message",
                "batch-nudge hook is not moving this; prefer scripts that run "
                "a whole read-only chain and report once",
            ),
        )
    big = _num(m, "bash_big_result_share")
    if big > BASH_BIG_SHARE:
        out.append(
            Lever(
                "agent mechanics",
                "Large Bash results",
                f"{big:.0%} of Bash result tokens come from results over 2k "
                f"({_num(m, 'bash_tokens_per_day'):,.0f} tokens/day)",
                "read files with ranges (sed -n 'a,bp', grep -n), never cat a "
                "whole file; cap every pipeline stage, not just the last",
            ),
        )
    if prev is not None:
        before = _num(prev, "standing_tokens_est")
        now = _num(m, "standing_tokens_est")
        if before and (now - before) / before > PREFIX_GROWTH:
            out.append(
                Lever(
                    "standing prefix",
                    "Always-loaded context grew",
                    f"{before:,.0f} -> {now:,.0f} est tokens per call",
                    "compact the surfaces that grew (see checkup); archive "
                    "finished memory entries",
                ),
            )
    if _num(m, "image_usd_share") > IMAGE_SHARE:
        out.append(
            Lever(
                "agent mechanics",
                "Images held in context",
                f"{_num(m, 'image_usd_share'):.0%} of spend",
                "extend the shrink hook to the tools returning screenshots",
            ),
        )
    return out


def _dead(dead_mcp: list[str], dead_skills: list[str]) -> list[Lever]:
    """Registered surfaces nobody used in either window."""
    if not dead_mcp and not dead_skills:
        return []
    return [
        Lever(
            "standing prefix",
            "Unused MCP servers / skills",
            f"MCP: {', '.join(dead_mcp) or '-'}; "
            f"skills: {', '.join(dead_skills) or '-'}",
            "park them (mcp_park.sh / move skill dir to backups/skills-parked)",
        ),
    ]


def candidates(
    metrics: dict[str, Any],
    previous: dict[str, Any] | None,
    dead_mcp: list[str],
    dead_skills: list[str],
) -> list[Lever]:
    """Every lever whose rule fired, sized ones first by daily saving."""
    levers = (
        _subagents(metrics)
        + _shape(metrics)
        + _mechanics(metrics, previous)
        + _dead(dead_mcp, dead_skills)
    )
    return sorted(levers, key=lambda lv: -(lv.est_usd_per_day or 0.0))


def render(levers: list[Lever]) -> list[str]:
    """Markdown table of the candidates."""
    if not levers:
        return ["_No rule fired._"]
    out = [
        "| category | lever | evidence | est $/day | action |",
        "|---|---|---|---|---|",
    ]
    for lv in levers:
        est = f"${lv.est_usd_per_day:,.2f}" if lv.est_usd_per_day else "-"
        out.append(
            f"| {lv.category} | {lv.title} | {lv.evidence} | {est} | {lv.action} |"
        )
    return out
