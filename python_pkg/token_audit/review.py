"""The "since last time" half of the report: comparison, ledger, candidates.

Kept apart from :mod:`report` (the per-window tables) because everything here
depends on state outside the window -- the previous snapshot, the ledger, the
registered MCP servers and skills -- and so is exactly the part a re-run must
reproduce from durable files rather than from transcripts that expire.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from python_pkg.token_audit import history, recommend, surfaces, unused

if TYPE_CHECKING:
    from python_pkg.token_audit.attribute import Axes, Totals

SNAPSHOT_VERSION = 2
# Metrics compared run-over-run; all are rates, never window totals, because
# windows differ in length (the "up 122%" of 2026-10-04 compared 37 days to 7).
COMPARED: tuple[str, ...] = (
    "usd_per_commit",
    "usd_per_day",
    "usd_per_call",
    "calls_per_day",
    "subagent_usd_share",
    "over_budget_usd_share",
    "home_cwd_usd_share",
    "batching_calls_per_msg",
    "bash_tokens_per_call",
    "standing_tokens_est",
)


def extra_metrics(totals: Totals, axes: Axes) -> dict[str, float]:
    """Metrics that come from the token axes rather than from dollars."""
    bash_calls = axes.tool_calls.get("Bash", 0)
    standing = sum(s.est_tokens for s in surfaces.collect())
    return {
        "batching_calls_per_msg": round(axes.batching.per_message, 3),
        "bash_tokens_per_call": (
            round(axes.tool_tokens.get("Bash", 0) / bash_calls, 1)
            if bash_calls
            else 0.0
        ),
        "image_usd_share": (
            round(axes.image_cost / totals.weighted, 4) if totals.weighted else 0.0
        ),
        "standing_tokens_est": standing,
    }


def _comparison(now: dict[str, Any], prev: dict[str, Any] | None) -> list[str]:
    """Rate-by-rate table against the previous comparable snapshot."""
    if prev is None or prev.get("v", 1) < SNAPSHOT_VERSION:
        return [
            "_No comparable previous snapshot (pre-2026-10-04 reports counted "
            "every API call ~1.9x and omitted subagents; do not compare against "
            "them). The next run will show deltas._",
        ]
    before = prev.get("metrics", {})
    out = ["| metric | previous | now | change |", "|---|---|---|---|"]
    for key in COMPARED:
        old, new = before.get(key), now.get(key)
        if not isinstance(old, (int, float)) or not isinstance(new, (int, float)):
            continue
        change = f"{(new - old) / old * 100:+.1f}%" if old else "n/a"
        out.append(f"| {key} | {old:,} | {new:,} | {change} |")
    return out


def _cell(value: float | None) -> str:
    """A ledger table cell: the number, or a dash when there is none."""
    return "-" if value is None else str(value)


def _ledger(snap: dict[str, Any]) -> list[str]:
    """Score every applied lever against the current metrics."""
    verdicts = history.score(history.read_ledger(), snap)
    if not verdicts:
        return ["_Ledger empty: nothing applied yet._"]
    out = [
        "| date-applied lever | metric | baseline | predicted | now | outcome | note |",
        "|---|---|---|---|---|---|---|",
    ]
    out += [
        f"| {v.lever} | {v.metric} | {v.baseline:,} | {_cell(v.predicted)} "
        f"| {_cell(v.actual)} | **{v.outcome}** | {v.note} |"
        for v in verdicts
    ]
    return out


def render(
    snap: dict[str, Any], prev: dict[str, Any] | None, *, levers: bool
) -> list[str]:
    """Markdown for comparison, ledger and (optionally) candidate levers."""
    lines = ["## Since the previous analysis", ""]
    lines += _comparison(snap["metrics"], prev)
    lines += ["", "## What helped (ledger)", ""]
    lines += _ledger(snap)
    if levers:
        dead_mcp = [u.name for u in unused.mcp_usage() if u.dead]
        dead_skills = [u.name for u in unused.skill_usage() if u.dead]
        prev_metrics = (
            prev.get("metrics")
            if prev and prev.get("v", 1) >= SNAPSHOT_VERSION
            else None
        )
        found = recommend.candidates(
            snap["metrics"], prev_metrics, dead_mcp, dead_skills
        )
        lines += ["", "## Candidate levers (rule-based)", ""]
        lines += recommend.render(found)
    return lines
