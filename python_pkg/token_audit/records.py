"""Record-level helpers: timestamps, the time window, and per-message dedupe.

Claude Code writes ONE API message as SEVERAL transcript records -- one per
content block (thinking, text, each ``tool_use``) -- and every one of them
carries the same, complete ``usage`` block. Summing usage per record therefore
counts each API call once per block. Measured 2026-10-04 over 32 days: 74,937
records for 40,388 real calls, a 1.9x overstatement that every report before
that date carried. :class:`TurnMerger` collapses the records back into one
:class:`Turn` per ``message.id``.

The window is applied per record, by its own ``timestamp``, because a file's
mtime only says when the session was last active: a session started three weeks
ago and touched today would otherwise count three weeks of spend as "this week".
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from python_pkg.token_audit.model import Turn

# Window bounds as unix seconds, inclusive at both ends.
Window = tuple[float, float]

# Names under which the 1h / 5m cache-write split is stored on a Turn's usage.
# They are deliberately NOT in model.TOKEN_KINDS: the reconciled weighted total
# keeps its historical definition, while pricing reads the split when present.
CACHE_1H = "cache_creation_1h"
CACHE_5M = "cache_creation_5m"


def timestamp(record: dict[str, Any]) -> float | None:
    """Return a record's ISO timestamp as unix seconds, or ``None``."""
    raw = record.get("timestamp")
    if not isinstance(raw, str):
        return None
    try:
        return datetime.fromisoformat(raw).timestamp()
    except ValueError:
        return None


def in_window(record: dict[str, Any], window: Window | None) -> bool:
    """Whether a record falls inside the window; undated records are kept."""
    if window is None:
        return True
    stamp = timestamp(record)
    return stamp is None or window[0] <= stamp <= window[1]


def cache_split(usage: dict[str, Any]) -> dict[str, int]:
    """Extract the 1h / 5m cache-write split from a raw usage block.

    A 1h cache write bills at 2x input and a 5m one at 1.25x, so the split is
    worth up to 60% of the cache-write cost. Claude Code currently writes 1h.
    """
    nested = usage.get("cache_creation")
    if not isinstance(nested, dict):
        return {}
    out: dict[str, int] = {}
    for key, name in (
        ("ephemeral_1h_input_tokens", CACHE_1H),
        ("ephemeral_5m_input_tokens", CACHE_5M),
    ):
        value = nested.get(key)
        if isinstance(value, int):
            out[name] = value
    return out


def merge(held: Turn, extra: Turn) -> Turn:
    """Fold a second record of the same API message into the first.

    Usage is the same block repeated, so the max per key is taken (robust to a
    record written before ``output_tokens`` was final). Tool calls are spread
    across the records -- one per ``tool_use`` block -- so those are summed.
    """
    keys = held.usage.keys() | extra.usage.keys()
    usage = {k: max(held.usage.get(k, 0), extra.usage.get(k, 0)) for k in keys}
    return replace(
        held,
        usage=usage,
        context=max(held.context, extra.context),
        tool_calls=held.tool_calls + extra.tool_calls,
    )


class TurnMerger:
    """Collapse consecutive same-id records into one turn, drop late repeats."""

    def __init__(self) -> None:
        """Start with nothing held and no ids seen."""
        self._held: Turn | None = None
        self._seen: set[str] = set()

    def push(self, turn: Turn) -> Turn | None:
        """Accept one record's turn; return a completed turn if one is ready."""
        held = self._held
        if held is not None and turn.message_id and turn.message_id == held.message_id:
            self._held = merge(held, turn)
            return None
        done = self.flush()
        if turn.message_id and turn.message_id in self._seen:
            return done
        if turn.message_id:
            self._seen.add(turn.message_id)
        self._held = turn
        return done

    def flush(self) -> Turn | None:
        """Release the held turn, if any."""
        done, self._held = self._held, None
        return done
