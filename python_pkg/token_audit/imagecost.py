"""Estimate what images cost *after* the turn that loaded them.

An image does not leave the context once read. Every subsequent request in the
session re-sends it as cache-read, so a screenshot loaded at turn 20 of a
1000-turn session is paid for ~980 more times. At the cache-read weight of 0.1
that turns ~2.5k tokens into ~250k, which is why images are worth tracking as
their own axis rather than lumping them in with text tool results.

Measured over a real 7-day window this amplification was ~1.6% of weighted
spend — real, but an order of magnitude below session length. An earlier
version of this module reported ~27%, because it sized images by their base64
payload length; see :func:`parse._result_tokens` for why that is ~20x too high.
The lesson is kept here deliberately: an estimate that is never checked against
billed tokens can invent a headline finding out of nothing.

Two honest limits on the number this produces:

* It is an **estimate**, derived from result sizes rather than billed tokens.
  It is deliberately never folded into the reconciled totals, which come only
  from the API's own usage figures.
* Compaction discards history. An image loaded before a compaction stops being
  re-sent, so charging it forever would roughly double the figure and yields
  the impossible result of sessions costing more than they measurably did.
  Compaction is detected from a sharp drop in context size.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from python_pkg.token_audit.model import (
    COMPACTION_DROP_RATIO,
    WEIGHTS,
    Session,
    ToolCall,
    Turn,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

# Images are re-sent from cache, so each later turn charges them at cache-read.
_REREAD_WEIGHT = WEIGHTS["cache_read_input_tokens"]


def _is_compaction(context: int, previous: int | None) -> bool:
    """Whether this turn's context implies history was just discarded.

    Context grows monotonically as a session accumulates messages, so the only
    way it falls sharply is compaction (or a fresh branch). A ratio test rather
    than an absolute threshold keeps this valid for both small and huge
    sessions.
    """
    return previous is not None and context < previous * COMPACTION_DROP_RATIO


def image_cost(events: Iterable[tuple[str, object]]) -> float:
    """Return cost-weighted tokens spent re-sending images across turns.

    ``events`` must preserve transcript order — the whole calculation is about
    how many turns followed each image before compaction cleared it.
    """
    live: list[int] = []
    previous: int | None = None
    total = 0.0
    for kind, event in events:
        if kind == "tool":
            if isinstance(event, ToolCall) and event.is_image:
                live.append(event.result_tokens)
        elif isinstance(event, Turn):
            if _is_compaction(event.context, previous):
                live.clear()
            # Charge every still-live image once for this turn: it was part of
            # the context this request re-sent.
            total += sum(live) * _REREAD_WEIGHT
            previous = event.context
    return total


def annotate(session: Session, events: Iterable[tuple[str, object]]) -> Session:
    """Attach the image amplification estimate to a session."""
    session.image_cost = image_cost(events)
    return session
