"""Active time: the sum of gaps between consecutive records, ignoring idle gaps.

A gap longer than :data:`IDLE_GAP` contributes **zero** (not the cap): it means
nobody and nothing was working. Storing each file as maximal runs of records
spaced at most ``IDLE_GAP`` apart is lossless for that rule -- the active time
of several files' merged timeline equals the measure of the union of their runs
with gaps of up to ``IDLE_GAP`` between runs bridged. That is what lets a main
session and the subagents it spawned, ingested in different runs, combine
exactly afterwards.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

IDLE_GAP = 300.0
Span = tuple[float, float]


def intervals(stamps: Iterable[float], gap: float = IDLE_GAP) -> list[Span]:
    """Collapse sorted-or-not timestamps into maximal runs."""
    out: list[Span] = []
    for stamp in sorted(stamps):
        if out and stamp - out[-1][1] <= gap:
            out[-1] = (out[-1][0], stamp)
        else:
            out.append((stamp, stamp))
    return out


def measure(
    spans: Iterable[Span],
    low: float = float("-inf"),
    high: float = float("inf"),
    gap: float = IDLE_GAP,
) -> float:
    """Active seconds of the union of runs, clipped to ``[low, high)``."""
    merged = intervals_union(spans, gap)
    total = 0.0
    for start, end in merged:
        total += max(0.0, min(end, high) - max(start, low))
    return total


def intervals_union(spans: Iterable[Span], gap: float = IDLE_GAP) -> list[Span]:
    """Union of runs, bridging gaps no longer than ``gap``."""
    out: list[Span] = []
    for start, end in sorted(spans):
        if out and start - out[-1][1] <= gap:
            out[-1] = (out[-1][0], max(out[-1][1], end))
        else:
            out.append((start, end))
    return out
