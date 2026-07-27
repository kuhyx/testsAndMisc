"""Pure planning helpers for the background worker.

Nothing here performs IO, so every scheduling and retry decision is testable
from plain values. The worker in :mod:`python_pkg.wsg_grabber.downloader` is a
thin shell that calls these and then acts.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from python_pkg.wsg_grabber.constants import (
    BACKOFF_BASE_S,
    BACKOFF_CAP_S,
    MIN_REQUEST_INTERVAL_S,
)
from python_pkg.wsg_grabber.models import ResumePlan, TaskKind

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from python_pkg.wsg_grabber.models import ThreadRef


def choose_task(
    pending_downloads: int,
    stale_thread_count: int,
    *,
    catalog_fresh: bool,
) -> TaskKind:
    """Decide what the worker should do next.

    Downloads win over scanning so the reviewer gets its first playable video
    as soon as possible, which is the whole point of loading in the background.

    Args:
        pending_downloads: Files known but not yet fetched.
        stale_thread_count: Threads whose contents may have changed.
        catalog_fresh: Whether the thread list has been read at least once this
            cycle.

    Returns:
        TaskKind: The next action.
    """
    if pending_downloads > 0:
        return TaskKind.DOWNLOAD
    if stale_thread_count > 0 or not catalog_fresh:
        return TaskKind.SCAN
    return TaskKind.IDLE


def stale_threads(
    known: Mapping[int, int],
    live: Sequence[ThreadRef],
) -> list[ThreadRef]:
    """Return threads worth fetching.

    A thread is worth fetching when it has never been seen, or when the board
    reports a newer ``last_modified`` than the one already stored. On a steady
    board this reduces a cycle to a single request.

    Args:
        known: Thread number mapped to the stored timestamp.
        live: Threads currently advertised by the board.

    Returns:
        list[ThreadRef]: Threads to fetch, in the order given.
    """
    return [
        ref
        for ref in live
        if ref.thread_no not in known or ref.api_last_modified > known[ref.thread_no]
    ]


def next_delay(last_request: float, now: float) -> float:
    """Return how long to wait before the next API request.

    The 4chan API rules ask for at most one request per second.

    Args:
        last_request: Monotonic timestamp of the previous request, or 0.
        now: Current monotonic timestamp.

    Returns:
        float: Seconds to sleep, never negative.
    """
    elapsed = now - last_request
    remaining = MIN_REQUEST_INTERVAL_S - elapsed
    return max(0.0, remaining)


def backoff_seconds(attempt: int, retry_after: float | None = None) -> float:
    """Return how long to pause after a rejected request.

    An explicit ``Retry-After`` always wins; otherwise the delay doubles per
    attempt up to a cap so a sustained block does not spin.

    Args:
        attempt: 1 for the first failure.
        retry_after: Server-supplied delay in seconds, when present.

    Returns:
        float: Seconds to wait, capped.
    """
    if retry_after is not None and retry_after > 0:
        return min(retry_after, BACKOFF_CAP_S)
    exponent = max(0, attempt - 1)
    return min(BACKOFF_BASE_S * (2.0**exponent), BACKOFF_CAP_S)


def parse_retry_after(header: str | None) -> float | None:
    """Read a ``Retry-After`` header expressed in seconds.

    The HTTP-date form is deliberately not handled; falling back to exponential
    backoff is safe and avoids a clock-skew dependency.

    Args:
        header: Raw header value, if any.

    Returns:
        float | None: Seconds to wait, or None when absent or not numeric.
    """
    if header is None:
        return None
    try:
        value = float(header.strip())
    except ValueError:
        return None
    return value if value >= 0 else None


def resume_plan(part_size: int, expected_size: int) -> ResumePlan:
    """Decide how to continue a partially downloaded file.

    Args:
        part_size: Bytes already on disk in the ``.part`` file.
        expected_size: Size the API says the file should be.

    Returns:
        ResumePlan: Byte offset to request, and whether to bin what is there.
    """
    if part_size <= 0:
        return ResumePlan(offset=0, discard=False)
    if 0 < expected_size <= part_size:
        return ResumePlan(offset=0, discard=True)
    return ResumePlan(offset=part_size, discard=False)
