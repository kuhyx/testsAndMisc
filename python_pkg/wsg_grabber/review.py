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

from python_pkg.wsg_grabber.models import (
    Downloaded,
    Emptiness,
    FileReady,
    Indexed,
    ReviewCommand,
    ReviewedItem,
    ScanFinished,
    Verdict,
    WorkerFailed,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from python_pkg.wsg_grabber.models import DownloadEvent, ReviewItem

_BYTES_PER_MIB = 1024 * 1024


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


def can_undo(state: SessionState) -> bool:
    """Report whether there is a verdict to take back.

    Args:
        state: Current state.

    Returns:
        bool: True when the index holds at least one reversible verdict.
    """
    return state.undoable > 0


def on_undo(state: SessionState, action: ReviewedItem) -> SessionState:
    """Show a restored video again after its verdict was reversed.

    The video currently on screen goes to the front of the queue, so changing
    your mind never skips anything.

    Args:
        state: Current state.
        action: The verdict that was just reversed on disk and in the index.

    Returns:
        SessionState: Updated state showing the restored video.
    """
    queue = list(state.pending)
    if state.current is not None:
        queue.insert(0, state.current)
    corrected = (
        replace(state, kept=max(0, state.kept - 1))
        if action.choice is Verdict.KEEP
        else replace(state, passed=max(0, state.passed - 1))
    )
    return replace(
        corrected,
        undoable=max(0, state.undoable - 1),
        pending=tuple(queue),
        current=action.item,
    )


def forget_last(state: SessionState) -> SessionState:
    """Drop one verdict from the undo count without reversing it.

    Used when the file is no longer where the verdict left it, so a second
    attempt does not keep failing on the same entry.

    Args:
        state: Current state.

    Returns:
        SessionState: Updated state.
    """
    return replace(state, undoable=max(0, state.undoable - 1))


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
    return replace(state, error=_worker_message(event))


def on_quit(state: SessionState) -> SessionState:
    """Mark the session as finishing.

    Args:
        state: Current state.

    Returns:
        SessionState: Updated state.
    """
    return replace(state, quitting=True)


def emptiness(state: SessionState) -> Emptiness:
    """Explain why there is nothing to show, if that is the case.

    Args:
        state: Current state.

    Returns:
        Emptiness: Whether the queue is merely waiting or genuinely exhausted.
    """
    if state.current is not None:
        return Emptiness.NOT_EMPTY
    return Emptiness.EXHAUSTED if state.scan_complete else Emptiness.WAITING


def status_line(state: SessionState) -> str:
    """Build the text under the video.

    Args:
        state: Current state.

    Returns:
        str: One line summarising progress.
    """
    if state.error is not None:
        return f"downloader stopped: {state.error}"
    counts = (
        f"kept {state.kept} · passed {state.passed} · "
        f"queued {len(state.pending)} · downloaded {state.downloaded}"
    )
    if state.indexed:
        counts = f"{counts}/{state.indexed}"
    undo = f" · u undoes ({state.undoable})" if state.undoable else ""
    mood = {
        Emptiness.NOT_EMPTY: "",
        Emptiness.WAITING: " · waiting for downloads…",
        Emptiness.EXHAUSTED: " · all caught up",
    }[emptiness(state)]
    return f"{counts}{mood}{undo}"


def filename_line(state: SessionState) -> str:
    """Describe the video currently on screen.

    Args:
        state: Current state.

    Returns:
        str: Original filename with size and dimensions, or a placeholder.
    """
    item = state.current
    if item is None:
        return "—"
    size = item.fsize / _BYTES_PER_MIB
    return f"{item.orig_name}  ·  {item.width}x{item.height}  ·  {size:.1f} MiB"


def title_line(state: SessionState) -> str:
    """Build the window title.

    Args:
        state: Current state.

    Returns:
        str: Title including the running verdict tally.
    """
    return f"/wsg/ — kept {state.kept}, passed {state.passed}"


def render(state: SessionState) -> ReviewCommand:
    """Turn the state into instructions the window applies verbatim.

    Args:
        state: Current state.

    Returns:
        ReviewCommand: Everything the GUI should show or do.
    """
    item = state.current
    return ReviewCommand(
        play=None if item is None else item.path,
        stop=item is None,
        status=status_line(state),
        title=title_line(state),
        filename=filename_line(state),
        verdicts_enabled=item is not None and not state.quitting,
        undo_enabled=can_undo(state) and not state.quitting,
        quit_app=state.quitting,
    )


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


def _worker_message(event: WorkerFailed) -> str:
    """Extract the message from a worker failure.

    Args:
        event: The failure report.

    Returns:
        str: Text for the status bar.
    """
    return event.message
