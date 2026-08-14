"""Render the audit as markdown plus a machine-readable snapshot.

Two outputs, two consumers. ``WEEKLY.md`` is for reading; ``weekly.json`` is
for the next run, which diffs against it to produce a week-over-week delta —
the part that makes running this repeatedly worth anything, since a single
week's absolute numbers cannot tell you whether a change helped.

Both land outside the repo, in ``~/.claude/token-report/``. The report names
paths and tools but never contains prompt or file *content*, so it stays safe
to keep on disk; it is still never committed, because the code repo is public
and the working-directory list alone maps out private projects.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import TYPE_CHECKING

from python_pkg.token_audit.attribute import LONG_SESSION_TURNS, Axes, Totals
from python_pkg.token_audit.model import TOKEN_KINDS

if TYPE_CHECKING:
    from collections.abc import Sequence

    from python_pkg.token_audit.model import Session

REPORT_DIR = Path.home() / ".claude" / "token-report"
MARKDOWN_NAME = "WEEKLY.md"
JSON_NAME = "weekly.json"
TOP_N = 12


@dataclass(frozen=True)
class Window:
    """The time span a report covers."""

    since: float
    until: float

    def describe(self) -> str:
        """Human-readable window bounds."""
        fmt = "%Y-%m-%d %H:%M"
        start = datetime.fromtimestamp(self.since, tz=UTC).strftime(fmt)
        end = datetime.fromtimestamp(self.until, tz=UTC).strftime(fmt)
        return f"{start} - {end} UTC"


def snapshot(totals: Totals, axes: Axes, window: Window, sessions: int) -> dict:
    """Build the JSON structure persisted for next week's delta."""
    return {
        "generated": datetime.now(tz=UTC).isoformat(),
        "window": {"since": window.since, "until": window.until},
        "sessions": sessions,
        "turns": totals.turns,
        "weighted_total": round(totals.weighted),
        "raw": dict(totals.by_kind),
        "image_cost": round(axes.image_cost),
        "image_reads": axes.images.count,
        "cold_start_tokens": int(axes.cold_start.total),
        "cold_starts": axes.cold_start.count,
        "long_sessions": axes.long_sessions.count,
        "long_session_cost": round(axes.long_sessions.total),
        "sidechain_cost": round(axes.sidechain.total),
        "projects": dict(axes.project.most_common(TOP_N)),
        "mcp_calls": dict(axes.mcp_calls),
        "skills": dict(axes.skills),
    }


def _pct(part: float, whole: float) -> str:
    """Format ``part`` as a percentage of ``whole``, guarding divide-by-zero."""
    return f"{part / whole * 100:.1f}%" if whole else "n/a"


def _delta_line(current: dict, previous: dict | None) -> str:
    """Describe the change in weighted spend since the previous snapshot."""
    if previous is None:
        return "_No previous report on disk - next run will show a delta._"
    before = previous.get("weighted_total", 0)
    now = current["weighted_total"]
    if not before:
        return "_Previous report had no spend recorded._"
    change = (now - before) / before * 100
    arrow = "up" if change >= 0 else "down"
    return f"**Week over week: {arrow} {abs(change):.1f}%** ({before:,} -> {now:,})"


def _table(rows: Sequence[tuple[str, str]], headers: tuple[str, str]) -> list[str]:
    """Render a two-column markdown table."""
    out = [f"| {headers[0]} | {headers[1]} |", "|---|---|"]
    out += [f"| {left} | {right} |" for left, right in rows]
    return out


def render(
    totals: Totals,
    axes: Axes,
    window: Window,
    sessions: Sequence[Session],
    current: dict,
    previous: dict | None,
) -> str:
    """Render the full markdown report."""
    total = totals.weighted
    lines = [
        "# Claude Code token audit",
        "",
        f"Window: {window.describe()}",
        f"Sessions: {len(sessions)} | assistant turns: {totals.turns:,}",
        "",
        _delta_line(current, previous),
        "",
        "## Totals",
        "",
        f"**Cost-weighted total: {total:,.0f}**",
        "",
    ]
    lines += _table(
        [(kind, f"{totals.by_kind.get(kind, 0):,}") for kind in TOKEN_KINDS],
        ("raw token class", "count"),
    )
    lines += ["", "## Ranked drivers", ""]
    lines += _table(_driver_rows(axes, total), ("driver", "share of weighted cost"))
    lines += ["", "## Projects", ""]
    lines += _table(
        [
            (path, f"{_pct(cost, total)} ({cost:,})")
            for path, cost in axes.project.most_common(TOP_N)
        ],
        ("working directory", "weighted cost"),
    )
    lines += ["", "## Tool result payloads (estimated tokens returned)", ""]
    lines += _table(
        [
            (name, f"{tok:,} over {axes.tool_calls[name]:,} calls")
            for name, tok in axes.tool_tokens.most_common(TOP_N)
        ],
        ("tool", "result tokens"),
    )
    lines += ["", "## MCP servers invoked", ""]
    lines += _table(
        [(name, f"{n:,}") for name, n in axes.mcp_calls.most_common()]
        or [("(none invoked)", "0")],
        ("server", "calls"),
    )
    lines += ["", "## Skills invoked", ""]
    lines += _table(
        [(name, f"{n:,}") for name, n in axes.skills.most_common()]
        or [("(none invoked)", "0")],
        ("skill", "invocations"),
    )
    lines += ["", "## Most expensive sessions", ""]
    lines += _table(_session_rows(sessions, total), ("session", "weighted cost"))
    lines += ["", _footer(axes)]
    return "\n".join(lines) + "\n"


def _driver_rows(axes: Axes, total: float) -> list[tuple[str, str]]:
    """Rows for the headline driver table."""
    long_cost = axes.long_sessions.total
    return [
        (
            f"Images re-sent in context ({axes.images.count:,} reads)",
            f"{_pct(axes.image_cost, total)} ({axes.image_cost:,.0f})",
        ),
        (
            f"Sessions over {LONG_SESSION_TURNS} turns ({axes.long_sessions.count})",
            f"{_pct(long_cost, total)} ({long_cost:,.0f})",
        ),
        (
            f"Cold-start prefix ({axes.cold_start.count} starts)",
            f"{axes.cold_start.total:,.0f} raw tokens cached",
        ),
        (
            f"Subagent sidechains ({axes.sidechain.count} turns)",
            f"{_pct(axes.sidechain.total, total)} ({axes.sidechain.total:,.0f})",
        ),
    ]


def _session_rows(sessions: Sequence[Session], total: float) -> list[tuple[str, str]]:
    """Rows for the per-session table, most expensive first."""
    ranked = sorted(sessions, key=lambda s: s.cost, reverse=True)[:TOP_N]
    return [
        (
            f"`{s.session_id[:8]}` ({s.turn_count:,} turns, max ctx {s.max_context:,})",
            f"{_pct(s.cost, total)} ({s.cost:,.0f})",
        )
        for s in ranked
    ]


def _footer(axes: Axes) -> str:
    """Closing note on how the image figure should be read."""
    return (
        f"_Image cost is an estimate: {axes.images.total:,.0f} tokens were read once, "
        "then re-sent as cache-read on every later turn until compaction. "
        "It is excluded from the reconciled totals above, which come only from "
        "the API's reported usage._"
    )


def write(markdown: str, data: dict, directory: Path = REPORT_DIR) -> Path:
    """Persist both outputs, returning the markdown path."""
    directory.mkdir(parents=True, exist_ok=True)
    md_path = directory / MARKDOWN_NAME
    md_path.write_text(markdown, encoding="utf-8")
    (directory / JSON_NAME).write_text(json.dumps(data, indent=2), encoding="utf-8")
    return md_path


def load_previous(directory: Path = REPORT_DIR) -> dict | None:
    """Load the last snapshot, or ``None`` if this is the first run."""
    path = directory / JSON_NAME
    if not path.exists():
        return None
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return None
    return loaded if isinstance(loaded, dict) else None
