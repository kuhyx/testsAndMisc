"""Carry cost: what a tool result costs by staying in context afterwards.

A result of N tokens is cache-read again on every later API call of the same
file until a compaction drops it (or the session ends), so its real price is
N x (cache-read price of each later call) -- usually far more than the call
that fetched it. A compaction shows up as the context shrinking below
``COMPACTION_DROP_RATIO`` of the previous call's, the same rule token_audit's
image-cost model uses.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from python_pkg.token_audit.model import COMPACTION_DROP_RATIO
from python_pkg.token_audit.pricing import PER_MILLION, WRITE_5M

if TYPE_CHECKING:
    from python_pkg.token_audit.pricing import PriceBook


class _Row(Protocol):
    """Anything with creation / carry accumulators."""

    create_usd: float
    carry_usd: float
    carry_calls: int


class Tracker:
    """Collects calls and results in order, settles carry at the end."""

    def __init__(self) -> None:
        """Start with no calls and no results."""
        self.calls: list[tuple[str, int]] = []
        self.writes: list[float] = []
        self.results: list[tuple[int, int, _Row]] = []

    def turn(self, model: str, context: int, write: float = WRITE_5M) -> None:
        """Note one API call, in order, with its cache-write price multiplier."""
        self.calls.append((model, context))
        self.writes.append(write)

    def result(self, row: _Row, tokens: int) -> None:
        """Note a result arriving before call number ``len(self.calls)``."""
        self.results.append((len(self.calls), tokens, row))

    def spans(self) -> list[tuple[int, int, int, _Row]]:
        """``(first, end, tokens, row)``: the calls ``first..end-1`` carry it."""
        # cut[i]: index of the first call at or after i that starts a new
        # context (after a compaction), else len(calls).
        size = len(self.calls)
        cut = [size] * (size + 1)
        for index in range(size - 1, -1, -1):
            dropped = index > 0 and self.calls[index][1] < (
                COMPACTION_DROP_RATIO * self.calls[index - 1][1]
            )
            cut[index] = index if dropped else cut[index + 1]
        return [
            (start, cut[start + 1], tokens, row)
            for start, tokens, row in self.results
            if start < size
        ]

    def settle(self, book: PriceBook) -> None:
        """Add each result's creation and carry to its row.

        Creation: the first call after the result writes it to cache, at that
        call's write multiplier of input price. Carry: every call from there
        to the next compaction re-reads it at the cache-read price.
        """
        prefix = [0.0]
        for model, _ in self.calls:
            prefix.append(prefix[-1] + book.for_model(model).cache_read)
        for start, end, tokens, row in self.spans():
            price = book.for_model(self.calls[start][0]).input
            row.create_usd += tokens * self.writes[start] * price / PER_MILLION
            row.carry_usd += tokens * (prefix[end] - prefix[start]) / PER_MILLION
            row.carry_calls += end - start
