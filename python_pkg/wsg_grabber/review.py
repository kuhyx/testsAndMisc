"""The reviewer's behaviour, with no toolkit anywhere in sight.

This module is the whole application as far as behaviour is concerned. It
decides what plays next, what a verdict does, when the queue has run dry and
exactly what the status bar reads. :mod:`python_pkg.wsg_grabber.ui` only
applies the :class:`ReviewCommand` this produces, so every decision is testable
from plain values and none of them need a display.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

# Re-exported through __all__ so review.render / review.status_line and friends
# keep working for ui.py and test_review.py; the implementations live in
# _render to keep this module under the 250-line cap. _render only needs
# SessionState for typing, so this import is not circular at runtime.
from python_pkg.wsg_grabber._render import (
    emptiness,
    filename_line,
    render,
    status_line,
    title_line,
)
from python_pkg.wsg_grabber._undo import can_undo, forget_last, on_undo
from python_pkg.wsg_grabber.models import (
    Downloaded,
    FileReady,
    Indexed,
    ScanFinished,
    Verdict,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from python_pkg.wsg_grabber.models import DownloadEvent, ReviewItem

__all__ = [
    "SessionState",
    "can_undo",
    "emptiness",
    "filename_line",
    "forget_last",
    "initial_state",
    "on_event",
    "on_missing_locally",
    "on_new_files",
    "on_quit",
    "on_undo",
    "on_verdict",
    "render",
    "status_line",
    "title_line",
]


@dataclass(frozen=True, slots=True)
class SessionState:
    """Everything the reviewer knows, as one immutable value."""

    pending: tuple[ReviewItem, ...] = ()
    current: ReviewItem | None = None
    kept: int = 0
    passed: int = 0
    indexed: int = 0
    downloaded: int = 0
    scan_complete: bool = False
    quitting: bool = False
    error: str | None = None
    undoable: int = 0
    """Verdicts recorded in the index that could still be taken back."""


def initial_state(
    indexed: int,
    ready: Sequence[ReviewItem],
    undoable: int = 0,
) -> SessionState:
    """Build the state a session starts from.

    Args:
        indexed: How many files the index already knows about.
        ready: Videos downloaded on a previous run and still unreviewed.
        undoable: Verdicts already in the index that can still be reversed, so
            undo carries across restarts rather than starting empty.

    Returns:
        SessionState: Starting state, already showing the first video if any.
    """
    state = SessionState(indexed=indexed, undoable=undoable)
    return on_new_files(state, ready)


def on_new_files(state: SessionState, items: Sequence[ReviewItem]) -> SessionState:
    """Add freshly downloaded videos to the queue.

    The first arrival is promoted straight to the screen, which is what lets
    watching start while the rest of the board is still downloading.

    Args:
        state: Current state.
        items: Newly available videos.

    Returns:
        SessionState: Updated state.
    """
    if not items:
        return state
    queue = [*state.pending, *items]
    current = state.current
    if current is None:
        current = queue.pop(0)
    return replace(state, pending=tuple(queue), current=current)


def on_verdict(state: SessionState, choice: Verdict) -> SessionState:
    """Record a decision about the current video and advance.

    Args:
        state: Current state.
        choice: What the user pressed.

    Returns:
        SessionState: Updated state showing the next video.
    """
    if state.current is None:
        return state
    counted = (
        replace(state, kept=state.kept + 1)
        if choice is Verdict.KEEP
        else replace(state, passed=state.passed + 1)
    )
    return _advance(replace(counted, undoable=state.undoable + 1))


def on_missing_locally(state: SessionState) -> SessionState:
    """Drop the current video because its file has disappeared.

    Args:
        state: Current state.

    Returns:
        SessionState: Updated state showing the next video.
    """
    if state.current is None:
        return state
    return _advance(state)


def on_event(state: SessionState, event: DownloadEvent) -> SessionState:
    """Fold one background-worker event into the state.

    Args:
        state: Current state.
        event: What the worker reported.

    Returns:
        SessionState: Updated state.
    """
    if isinstance(event, FileReady):
        return on_new_files(state, [event.item])
    if isinstance(event, Indexed):
        return replace(state, indexed=event.known)
    if isinstance(event, Downloaded):
        return replace(state, downloaded=event.count)
    if isinstance(event, ScanFinished):
        return replace(state, scan_complete=True)
    return replace(state, error=event.message)


def on_quit(state: SessionState) -> SessionState:
    """Mark the session as finishing.

    Args:
        state: Current state.

    Returns:
        SessionState: Updated state.
    """
    return replace(state, quitting=True)


def _advance(state: SessionState) -> SessionState:
    """Move to the next queued video.

    Args:
        state: State whose current item has been dealt with.

    Returns:
        SessionState: Updated state.
    """
    queue = list(state.pending)
    following = queue.pop(0) if queue else None
    return replace(state, pending=tuple(queue), current=following)
