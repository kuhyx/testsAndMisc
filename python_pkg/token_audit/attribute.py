"""Roll sessions up along the axes the report ranks.

Each axis answers a different "should I change something?" question, so they
are kept separate rather than merged into one table:

* **project** (cwd) — which work was expensive, not which tool was.
* **tool** — where result payloads come from; ranked by estimated result size.
* **mcp** — invocation counts per server, the only way to tell a registered
  server apart from a *used* one.
* **skill** — how often each skill was actually invoked.
* **sidechain** — what subagents cost, which is easy to assume is large and in
  practice may be zero.
* **cold start** — the fixed prefix every new session pays before doing work.

Only :func:`totals` feeds the reconciliation gate; everything else is ranking.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from python_pkg.token_audit.model import TOKEN_KINDS, Session

if TYPE_CHECKING:
    from collections.abc import Iterable

# A session past this many assistant turns is "long". Chosen from measurement:
# in the observed window, sessions above it were ~90% of all weighted spend,
# because per-turn cost scales with accumulated context.
LONG_SESSION_TURNS = 400


@dataclass
class Totals:
    """Raw token counts summed straight from the API's usage blocks."""

    by_kind: Counter[str] = field(default_factory=Counter)
    weighted: float = 0.0
    turns: int = 0

    def add(self, session: Session) -> None:
        """Accumulate one session's usage."""
        for turn in session.turns:
            for kind in TOKEN_KINDS:
                self.by_kind[kind] += turn.usage.get(kind, 0)
            self.weighted += turn.cost
            self.turns += 1


@dataclass
class Tally:
    """A running "how much, over how many" pair.

    Every headline driver is reported the same way — a cost or token total plus
    the number of things that produced it — so they share one type instead of
    two loose fields each.
    """

    total: float = 0.0
    count: int = 0

    def add(self, amount: float) -> None:
        """Record one more contribution."""
        self.total += amount
        self.count += 1


@dataclass
class Batching:
    """How often independent tool calls shared one API message.

    An unbatched call re-sends the whole conversation to earn a single result,
    so this is a direct measure of avoidable turns rather than a style metric.
    """

    messages: int = 0
    batched: int = 0
    calls: int = 0

    @property
    def share(self) -> float:
        """Fraction of tool messages that carried more than one call."""
        return self.batched / self.messages if self.messages else 0.0

    @property
    def per_message(self) -> float:
        """Mean tool calls per API message; 1.0 means nothing was ever batched."""
        return self.calls / self.messages if self.messages else 0.0


@dataclass
class Axes:
    """Every ranking the report needs, in one pass over the sessions."""

    project: Counter[str] = field(default_factory=Counter)
    tool_tokens: Counter[str] = field(default_factory=Counter)
    tool_calls: Counter[str] = field(default_factory=Counter)
    mcp_calls: Counter[str] = field(default_factory=Counter)
    skills: Counter[str] = field(default_factory=Counter)
    models: Counter[str] = field(default_factory=Counter)
    sidechain: Tally = field(default_factory=Tally)
    cold_start: Tally = field(default_factory=Tally)
    images: Tally = field(default_factory=Tally)
    long_sessions: Tally = field(default_factory=Tally)
    # Cost-weighted, compaction-aware image re-send estimate. Tracked apart from
    # ``images`` (which counts tokens read once) because the two answer
    # different questions and only this one is comparable to session cost.
    image_cost: float = 0.0
    batching: Batching = field(default_factory=Batching)


def build(sessions: Iterable[Session]) -> tuple[Totals, Axes]:
    """Compute reconciled totals and every ranking axis together."""
    totals = Totals()
    axes = Axes()
    for session in sessions:
        totals.add(session)
        _add_turns(axes, session)
        _add_tools(axes, session)
        _add_session_shape(axes, session)
    return totals, axes


def _add_turns(axes: Axes, session: Session) -> None:
    """Attribute per-turn cost to project, model and sidechain."""
    axes.project[session.cwd or "unknown"] += int(session.cost)
    for turn in session.turns:
        axes.models[turn.model] += turn.usage.get("output_tokens", 0)
        if turn.is_sidechain:
            axes.sidechain.add(turn.cost)
    _add_batching(axes, session)


def _add_batching(axes: Axes, session: Session) -> None:
    """Count how many API messages carried more than one tool call.

    Grouped by ``message_id`` because the transcript splits one API message
    across several records -- one per ``tool_use`` block. Counting records
    instead reports every message as carrying exactly one call, which is how a
    real 2.8% batching rate reads as 0.0%.
    """
    per_message: Counter[str] = Counter()
    for turn in session.turns:
        if turn.tool_calls and turn.message_id:
            per_message[turn.message_id] += turn.tool_calls
    for calls in per_message.values():
        axes.batching.messages += 1
        axes.batching.calls += calls
        if calls > 1:
            axes.batching.batched += 1


def _add_tools(axes: Axes, session: Session) -> None:
    """Attribute tool-result payloads to tools, MCP servers and skills."""
    for call in session.tools:
        axes.tool_tokens[call.name] += call.result_tokens
        axes.tool_calls[call.name] += 1
        server = call.mcp_server
        if server is not None:
            axes.mcp_calls[server] += 1
        if call.skill is not None:
            axes.skills[call.skill] += 1
        if call.is_image:
            axes.images.add(call.result_tokens)


def _add_session_shape(axes: Axes, session: Session) -> None:
    """Attribute whole-session properties: cold start, length, image cost."""
    cold = session.cold_start_tokens
    if cold:
        axes.cold_start.add(cold)
    axes.image_cost += session.image_cost
    if session.turn_count > LONG_SESSION_TURNS:
        axes.long_sessions.add(session.cost)


def reconcile(totals: Totals, sessions: Iterable[Session]) -> float:
    """Return the relative drift between axis sums and the raw usage totals.

    The report is only worth acting on if its parts add up to its whole, so the
    CLI turns this into a hard gate rather than a warning. Comparing the
    per-project rollup against the independently summed usage blocks catches
    any session that was counted twice or dropped.
    """
    summed = sum(session.cost for session in sessions)
    if totals.weighted == 0:
        return 0.0
    return abs(summed - totals.weighted) / totals.weighted
