"""Turning reviewer state into the text and commands the window applies.

Split out of :mod:`python_pkg.wsg_grabber.review` to keep that module under the
250-line cap. Everything here is a pure function of :class:`SessionState`: no
toolkit, no I/O, no state transitions -- those stay in ``review``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from python_pkg.wsg_grabber.models import Emptiness, ReviewCommand

if TYPE_CHECKING:
    from python_pkg.wsg_grabber.review import SessionState

_BYTES_PER_MIB = 1024 * 1024


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
        undo_enabled=state.undoable > 0 and not state.quitting,
        quit_app=state.quitting,
    )
