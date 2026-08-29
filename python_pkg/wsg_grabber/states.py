"""The lifecycle of a single file, as a pure transition function.

``GONE`` is the load-bearing state. A full first pass over /wsg/ takes hours, so
threads fall off page 10 and files 404 between being catalogued and being
fetched. Without a terminal sink those files would be retried on every future
run forever.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final

from python_pkg.wsg_grabber.constants import MAX_ATTEMPTS

# ``str, Enum`` not ``StrEnum``: mypy targets 3.10, where ``StrEnum`` is absent
# and would collapse to ``Any``, disabling checking on every member below.


class FileState(StrEnum):
    """Where a file is in its lifecycle."""

    NEW = "new"
    DOWNLOADING = "downloading"
    READY = "ready"
    FAILED = "failed"
    CORRUPT = "corrupt"
    KEPT = "kept"
    PASSED = "passed"
    GONE = "gone"


class FileEvent(StrEnum):
    """Something that happened to a file."""

    CLAIMED = "claimed"
    COMPLETED = "completed"
    NOT_FOUND = "not_found"
    DELETED_UPSTREAM = "deleted_upstream"
    TRANSIENT_ERROR = "transient_error"
    CHECKSUM_MISMATCH = "checksum_mismatch"
    KEPT = "kept"
    PASSED = "passed"
    MISSING_LOCALLY = "missing_locally"


TERMINAL: Final[frozenset[FileState]] = frozenset(
    {FileState.KEPT, FileState.PASSED, FileState.GONE},
)

CLAIMABLE: Final[frozenset[FileState]] = frozenset(
    {FileState.NEW, FileState.FAILED, FileState.CORRUPT},
)


def is_terminal(state: FileState) -> bool:
    """Report whether *state* can never change again.

    Args:
        state: State to classify.

    Returns:
        bool: True when no further transition is possible.
    """
    return state in TERMINAL


def next_state(current: FileState, event: FileEvent, attempts: int) -> FileState:
    """Return the state *current* moves to on *event*.

    Args:
        current: The file's present state.
        event: What happened.
        attempts: Download attempts made so far, including the one that just
            failed. Retryable failures give up once this reaches
            ``MAX_ATTEMPTS``.

    Returns:
        FileState: The new state.

    Raises:
        ValueError: If the transition is not legal, which means a caller has a
            bug rather than the board behaving oddly.
    """
    if current in CLAIMABLE and event is FileEvent.CLAIMED:
        return FileState.DOWNLOADING
    if current in CLAIMABLE and event is FileEvent.DELETED_UPSTREAM:
        return FileState.GONE
    if current is FileState.DOWNLOADING:
        return _from_downloading(event, attempts)
    if current is FileState.READY:
        return _from_ready(event)
    msg = f"illegal transition: {current.value} + {event.value}"
    raise ValueError(msg)


def _from_downloading(event: FileEvent, attempts: int) -> FileState:
    """Resolve a transition out of ``DOWNLOADING``.

    Args:
        event: What happened.
        attempts: Download attempts made so far.

    Returns:
        FileState: The new state.

    Raises:
        ValueError: If *event* cannot follow ``DOWNLOADING``.
    """
    if event is FileEvent.COMPLETED:
        return FileState.READY
    if event is FileEvent.NOT_FOUND:
        return FileState.GONE
    exhausted = attempts >= MAX_ATTEMPTS
    if event is FileEvent.TRANSIENT_ERROR:
        return FileState.GONE if exhausted else FileState.FAILED
    if event is FileEvent.CHECKSUM_MISMATCH:
        return FileState.GONE if exhausted else FileState.CORRUPT
    msg = f"illegal transition: downloading + {event.value}"
    raise ValueError(msg)


def _from_ready(event: FileEvent) -> FileState:
    """Resolve a transition out of ``READY``.

    Upstream deletion is deliberately not handled here: once the bytes are on
    disk it no longer matters that the post was removed.

    Args:
        event: What happened.

    Returns:
        FileState: The new state.

    Raises:
        ValueError: If *event* cannot follow ``READY``.
    """
    if event is FileEvent.KEPT:
        return FileState.KEPT
    if event is FileEvent.PASSED:
        return FileState.PASSED
    if event is FileEvent.MISSING_LOCALLY:
        return FileState.GONE
    msg = f"illegal transition: ready + {event.value}"
    raise ValueError(msg)
