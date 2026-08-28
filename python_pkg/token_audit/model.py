"""Types and cost weights shared by every stage of the audit.

The whole package exists to answer one question — *what did last week actually
cost?* — and the answer depends entirely on how the four token classes are
weighted. Ranking by raw token count is actively misleading here: in a measured
7-day window cache reads were 99% of raw volume but only ~82% of weighted cost,
while output was 1.5% of volume and ~7.5% of cost. A report that ranked by raw
counts would point at the wrong culprits, so the weights live here as the single
source of truth rather than being re-derived per module.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Relative price of each token class, normalised so plain input == 1.0. These
# mirror Anthropic's published multipliers (cache write 1.25x, cache read 0.1x,
# output 5x); they are ratios, not currency, so the report stays valid whatever
# the absolute per-token price happens to be.
WEIGHTS: dict[str, float] = {
    "input_tokens": 1.0,
    "cache_creation_input_tokens": 1.25,
    "cache_read_input_tokens": 0.1,
    "output_tokens": 5.0,
}

# Token classes in the order they should appear in reports.
TOKEN_KINDS: tuple[str, ...] = (
    "input_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
    "output_tokens",
)

# A turn whose context is below this fraction of the previous turn's is treated
# as sitting after a compaction boundary. Compaction discards earlier messages,
# so images loaded before it stop being re-sent and must stop being charged.
# Without this the image estimate roughly doubles and produces the nonsense
# result of single sessions costing >100% of their own measured spend.
COMPACTION_DROP_RATIO = 0.7

# Extensions whose Read results arrive as images rather than text.
IMAGE_SUFFIXES: frozenset[str] = frozenset(
    {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"},
)


def weighted(usage: dict[str, int]) -> float:
    """Return the cost-weighted token total for one request's usage block."""
    return sum(WEIGHTS[kind] * usage.get(kind, 0) for kind in TOKEN_KINDS)


@dataclass(frozen=True)
class Turn:
    """One assistant response, with the token accounting the API reported.

    ``context`` is what the request actually re-sent (cache read + cache
    creation). It is the quantity that grows as a session accumulates history,
    and the quantity that collapses at a compaction boundary, so it drives both
    the session-length analysis and the image-amplification model.

    ``message_id`` is the API message id. One API message can be written to the
    transcript as SEVERAL JSONL records -- one per ``tool_use`` block -- all
    sharing the id. Counting records therefore overstates turns and makes every
    turn look like it carried exactly one tool call. Grouping by this id is what
    makes the batching ratio come out right (measured 2026-08-28: 2.8% batched,
    not the 0.0% a per-record count reports).
    """

    usage: dict[str, int]
    context: int
    model: str
    is_sidechain: bool
    message_id: str = ""
    tool_calls: int = 0

    @property
    def cost(self) -> float:
        """Cost-weighted tokens attributable to this turn."""
        return weighted(self.usage)


@dataclass(frozen=True)
class ToolCall:
    """A tool invocation paired with the size of the result it returned.

    ``result_tokens`` is an estimate: transcripts store the rendered result, so
    the character count divided by four is the best available proxy. It is used
    only for ranking tools against each other, never added to the reconciled
    totals, which come exclusively from the API's own usage numbers.
    """

    name: str
    result_tokens: int
    path: str | None = None
    skill: str | None = None

    @property
    def is_image(self) -> bool:
        """Whether this call returned an image rather than text."""
        if self.path is None:
            return False
        dot = self.path.rfind(".")
        return dot != -1 and self.path[dot:].lower() in IMAGE_SUFFIXES

    @property
    def mcp_server(self) -> str | None:
        """The MCP server this tool belongs to, or ``None`` for builtins."""
        parts = self.name.split("__")
        expected_parts = 3
        return parts[1] if len(parts) >= expected_parts and parts[0] == "mcp" else None


@dataclass
class Session:
    """Everything one transcript file contributes to the audit."""

    session_id: str
    path: str
    cwd: str | None = None
    turns: list[Turn] = field(default_factory=list)
    tools: list[ToolCall] = field(default_factory=list)
    # Cost-weighted tokens spent re-sending images that were still live in
    # context. Computed by :mod:`imagecost`, which needs the interleaved order
    # of images and turns and so cannot be derived from these lists alone.
    image_cost: float = 0.0

    @property
    def cost(self) -> float:
        """Cost-weighted tokens for the whole session."""
        return sum(turn.cost for turn in self.turns)

    @property
    def turn_count(self) -> int:
        """Number of assistant responses in the session."""
        return len(self.turns)

    @property
    def max_context(self) -> int:
        """Largest context this session ever re-sent in a single request."""
        return max((turn.context for turn in self.turns), default=0)

    @property
    def cold_start_tokens(self) -> int:
        """Tokens written to cache before any cache existed to read from.

        The first request of a session pays to cache the whole fixed prefix —
        system prompt, tool schemas, CLAUDE.md, rules and memories. Isolating it
        shows what every new session costs before it does any work.
        """
        return sum(
            turn.usage.get("cache_creation_input_tokens", 0)
            for turn in self.turns
            if turn.usage.get("cache_read_input_tokens", 0) == 0
        )
