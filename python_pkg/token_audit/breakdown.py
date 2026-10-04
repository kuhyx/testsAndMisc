"""Dollar-denominated metrics: per model, per subagent, per call position.

:mod:`attribute` answers "where did the weighted tokens go"; this module puts
list-price dollars on the same sessions so that model choice becomes visible,
and computes the flat ``metrics`` dict every snapshot stores. Ledger entries
name a key in that dict, so a key here is a contract -- rename one and old
ledger lines silently become "unmeasured".
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import TYPE_CHECKING

from python_pkg.token_audit.pricing import usd

if TYPE_CHECKING:
    from collections.abc import Sequence

    from python_pkg.token_audit.model import Session
    from python_pkg.token_audit.pricing import PriceBook

SECONDS_PER_DAY = 86400
# Context size above which a call is "over budget" -- the session gate blocks
# here. Measured 2026-10-04: per-call cost 21k weighted for calls 1-100 versus
# 51k for calls 201-400, driven by context size, not by call count.
CONTEXT_BUDGET = 300_000
# Model a mechanical subagent would move to; used only to size that lever.
CHEAPER_MODEL = "claude-sonnet-5-5"
# Call-position buckets for the cost curve (upper bounds, inclusive).
BUCKETS: tuple[int, ...] = (100, 200, 400, 600, 1000)


@dataclass
class Tally:
    """Dollars and API calls accumulated along one axis."""

    usd: float = 0.0
    calls: int = 0

    def add(self, cost: float) -> None:
        """Count one call costing ``cost`` dollars."""
        self.usd += cost
        self.calls += 1


@dataclass
class Span:
    """Earliest and latest record timestamp seen (0.0 means none yet)."""

    earliest: float = 0.0
    latest: float = 0.0


@dataclass
class Breakdown:
    """Everything priced in one pass over the sessions."""

    main: Tally = field(default_factory=Tally)
    sub: Tally = field(default_factory=Tally)
    over_budget: Tally = field(default_factory=Tally)
    home_usd: float = 0.0
    by_model: Counter[str] = field(default_factory=Counter)
    by_agent_type: Counter[str] = field(default_factory=Counter)
    by_description: Counter[str] = field(default_factory=Counter)
    sub_opus_usd: float = 0.0
    # The same Opus subagent turns re-priced at the reference cheaper model:
    # what routing them there would have cost, for sizing that lever exactly.
    sub_opus_repriced_usd: float = 0.0
    buckets: dict[str, Tally] = field(default_factory=dict)
    commits: int = 0
    span: Span = field(default_factory=Span)

    @property
    def usd_main(self) -> float:
        """Main-conversation spend."""
        return self.main.usd

    @property
    def usd_sub(self) -> float:
        """Subagent spend."""
        return self.sub.usd

    @property
    def calls_main(self) -> int:
        """Main-conversation API calls."""
        return self.main.calls

    @property
    def calls_sub(self) -> int:
        """Subagent API calls."""
        return self.sub.calls

    @property
    def over_budget_calls(self) -> int:
        """Calls whose context exceeded :data:`CONTEXT_BUDGET`."""
        return self.over_budget.calls

    @property
    def over_budget_usd(self) -> float:
        """Spend carried by calls over the context budget."""
        return self.over_budget.usd

    @property
    def earliest(self) -> float:
        """Earliest record timestamp seen."""
        return self.span.earliest

    @property
    def latest(self) -> float:
        """Latest record timestamp seen."""
        return self.span.latest

    @property
    def usd_total(self) -> float:
        """Main plus subagent spend."""
        return self.usd_main + self.usd_sub

    @property
    def calls(self) -> int:
        """Real API calls, main plus subagent."""
        return self.calls_main + self.calls_sub

    @property
    def days(self) -> float:
        """Span actually covered by records, at least a minute's worth."""
        return max(self.latest - self.earliest, 60.0) / SECONDS_PER_DAY


def _bucket(index: int) -> str:
    """Label the call-position bucket a 1-based call index falls in."""
    low = 1
    for high in BUCKETS:
        if index <= high:
            return f"{low}-{high}"
        low = high + 1
    return f"{low}+"


def _stamp(found: Breakdown, stamp: float) -> None:
    """Widen the observed record span to include ``stamp``."""
    if not stamp:
        return
    span = found.span
    span.earliest = min(span.earliest or stamp, stamp)
    span.latest = max(span.latest, stamp)


def build(sessions: Sequence[Session], book: PriceBook) -> Breakdown:
    """Price every turn and roll it up along each axis."""
    found = Breakdown()
    home = str(Path.home())
    for session in sessions:
        is_sub = session.parent_id is not None
        found.commits += sum(1 for call in session.tools if call.commit)
        for index, turn in enumerate(session.turns, start=1):
            cost = usd(turn, book)
            _stamp(found, turn.timestamp)
            found.by_model[turn.model] += cost
            if turn.context > CONTEXT_BUDGET:
                found.over_budget.add(cost)
            if session.cwd == home:
                found.home_usd += cost
            if is_sub:
                found.sub.add(cost)
                found.by_agent_type[session.agent_type or "unknown"] += cost
                found.by_description[session.description or "?"] += cost
                if "opus" in turn.model:
                    found.sub_opus_usd += cost
                    cheap = replace(turn, model=CHEAPER_MODEL)
                    found.sub_opus_repriced_usd += usd(cheap, book)
            else:
                found.main.add(cost)
                found.buckets.setdefault(_bucket(index), Tally()).add(cost)
    return found


def _share(part: float, whole: float) -> float:
    """``part / whole`` rounded for storage, 0 when ``whole`` is 0."""
    return round(part / whole, 4) if whole else 0.0


def metrics(found: Breakdown) -> dict[str, float]:
    """The flat metric dict snapshots store and ledger entries reference."""
    total = found.usd_total
    opus_main = sum(c for m, c in found.by_model.items() if "opus" in m)
    return {
        "usd_total": round(total, 2),
        "usd_per_day": round(total / found.days, 2),
        "usd_per_call": round(total / found.calls, 5) if found.calls else 0.0,
        "calls": found.calls,
        "calls_per_day": round(found.calls / found.days, 1),
        "commits": found.commits,
        "usd_per_commit": round(total / found.commits, 2) if found.commits else 0.0,
        "subagent_usd_share": _share(found.usd_sub, total),
        "subagent_opus_usd_share": _share(found.sub_opus_usd, found.usd_sub),
        "opus_usd_share": _share(opus_main, total),
        "home_cwd_usd_share": _share(found.home_usd, total),
        "over_budget_call_share": _share(found.over_budget_calls, found.calls),
        "over_budget_usd_share": _share(found.over_budget_usd, total),
        "subagent_sonnet_saving_usd": round(
            found.sub_opus_usd - found.sub_opus_repriced_usd, 2
        ),
    }


def _money(rows: list[tuple[str, float]], total: float) -> list[str]:
    """Render ``(label, usd)`` rows as a markdown table with shares."""
    out = ["| item | USD | share |", "|---|---|---|"]
    out += [f"| {k} | ${v:,.2f} | {_share(v, total) * 100:.1f}% |" for k, v in rows]
    return out


def render(found: Breakdown, top: int = 12) -> list[str]:
    """Markdown sections for the dollar view."""
    total = found.usd_total
    lines = [
        "## Dollar view (list prices, deduplicated per API message)",
        "",
        f"**${total:,.2f}** over {found.days:.1f} days of records "
        f"({found.calls:,} API calls; main ${found.usd_main:,.2f}, "
        f"subagents ${found.usd_sub:,.2f}).",
        f"Calls with context over {CONTEXT_BUDGET:,} tokens: "
        f"{found.over_budget_calls:,} carrying "
        f"{_share(found.over_budget_usd, total) * 100:.1f}% of spend.",
        "",
        "### By model",
        "",
    ]
    lines += _money(found.by_model.most_common(top), total)
    lines += ["", "### Subagents by type", ""]
    lines += _money(found.by_agent_type.most_common(top), total)
    lines += ["", "### Costliest subagent tasks", ""]
    lines += _money(found.by_description.most_common(top), total)
    lines += ["", "### Cost per call by position in session (main only)", ""]
    lines += ["| calls | USD per call | calls |", "|---|---|---|"]
    for label in sorted(found.buckets, key=lambda b: int(b.split("-")[0].rstrip("+"))):
        tally = found.buckets[label]
        lines.append(f"| {label} | ${tally.usd / tally.calls:.4f} | {tally.calls:,} |")
    return lines
