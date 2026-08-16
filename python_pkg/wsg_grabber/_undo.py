"""Taking verdicts back.

Split out of :mod:`python_pkg.wsg_grabber.review` to keep that module under the
250-line cap. Undo is its own concern: it has to correct the running tally,
put the video that was on screen back at the front of the queue, and cope with
a file that has since moved -- none of which the forward path cares about.
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from python_pkg.wsg_grabber.models import Verdict

if TYPE_CHECKING:
    from python_pkg.wsg_grabber.models import ReviewedItem
    from python_pkg.wsg_grabber.review import SessionState


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
