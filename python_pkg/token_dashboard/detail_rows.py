"""Row types for the detail tables: one tool call, one context mark, one turn.

Each call and mark carries a :class:`Cost` (see :mod:`carry`): what putting
the chunk into the prompt cache cost, and what re-reading it on every later
call of the same file cost until a compaction dropped it.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Cost:
    """Creation + carry of one chunk of context, and the calls that carried it."""

    create_usd: float = 0.0
    carry_usd: float = 0.0
    carry_calls: int = 0


@dataclass(frozen=True)
class Where:
    """When something happened: prompt index, timestamp, serving model."""

    prompt_idx: int
    ts: float
    model: str


@dataclass
class CallRow:
    """One tool call, paired with its result (``error_kind`` empty when ok)."""

    where: Where
    name: str
    family: str
    target: str
    sig: str
    message_id: str
    end_ts: float = 0.0
    batch: int = 1
    result_tokens: int = 0
    images: int = 0
    error_kind: str = ""
    cost: Cost = field(default_factory=Cost)


@dataclass
class MarkRow:
    """Something that entered (or touched) context without being a tool call.

    ``kind`` is one of ``hook_run``, ``hook_context``, ``hook_block``,
    ``hook_error``, ``hook_msg``, ``attach``, ``compaction``, ``api_error``,
    ``interrupt``, ``image``. Rows with the same prompt, kind, name, detail
    and model are summed into one, with ``count`` occurrences.
    """

    where: Where
    kind: str
    name: str
    detail: str = ""
    count: int = 1
    tokens: int = 0
    extra: int = 0
    duration_ms: int = 0
    retry_usd: float = 0.0
    cost: Cost = field(default_factory=Cost)


@dataclass(frozen=True)
class TurnDetail:
    """Per-API-call facts the ``turns`` table does not hold."""

    where: Where
    latency_s: float
    cw_1h: int
    cw_5m: int
    out_text: int
    out_tool: int
    out_think: int
    tool_calls: int


@dataclass
class DetailRows:
    """Everything one file contributes to the detail tables."""

    calls: list[CallRow] = field(default_factory=list)
    marks: list[MarkRow] = field(default_factory=list)
    turns: list[TurnDetail] = field(default_factory=list)
