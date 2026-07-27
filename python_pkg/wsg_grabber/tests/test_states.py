"""Tests for the file lifecycle transition function."""

from __future__ import annotations

import pytest

from python_pkg.wsg_grabber.constants import MAX_ATTEMPTS
from python_pkg.wsg_grabber.states import (
    CLAIMABLE,
    TERMINAL,
    FileEvent,
    FileState,
    is_terminal,
    next_state,
)


@pytest.mark.parametrize("state", sorted(CLAIMABLE))
def test_claiming_starts_a_download(state: FileState) -> None:
    assert next_state(state, FileEvent.CLAIMED, 0) is FileState.DOWNLOADING


@pytest.mark.parametrize("state", sorted(CLAIMABLE))
def test_upstream_deletion_before_download_is_terminal(state: FileState) -> None:
    assert next_state(state, FileEvent.DELETED_UPSTREAM, 0) is FileState.GONE


def test_completed_download_becomes_reviewable() -> None:
    assert next_state(FileState.DOWNLOADING, FileEvent.COMPLETED, 1) is FileState.READY


def test_missing_upstream_file_is_never_retried() -> None:
    assert next_state(FileState.DOWNLOADING, FileEvent.NOT_FOUND, 1) is FileState.GONE


def test_transient_error_retries_until_the_attempt_budget_runs_out() -> None:
    assert (
        next_state(FileState.DOWNLOADING, FileEvent.TRANSIENT_ERROR, 1)
        is FileState.FAILED
    )
    assert (
        next_state(FileState.DOWNLOADING, FileEvent.TRANSIENT_ERROR, MAX_ATTEMPTS)
        is FileState.GONE
    )


def test_checksum_mismatch_retries_until_the_attempt_budget_runs_out() -> None:
    assert (
        next_state(FileState.DOWNLOADING, FileEvent.CHECKSUM_MISMATCH, 1)
        is FileState.CORRUPT
    )
    assert (
        next_state(FileState.DOWNLOADING, FileEvent.CHECKSUM_MISMATCH, MAX_ATTEMPTS)
        is FileState.GONE
    )


def test_verdicts_are_terminal() -> None:
    assert next_state(FileState.READY, FileEvent.KEPT, 1) is FileState.KEPT
    assert next_state(FileState.READY, FileEvent.PASSED, 1) is FileState.PASSED


def test_a_vanished_local_file_is_written_off() -> None:
    assert next_state(FileState.READY, FileEvent.MISSING_LOCALLY, 1) is FileState.GONE


def test_ready_ignores_upstream_deletion() -> None:
    """The bytes are already ours; the post being deleted is irrelevant."""
    with pytest.raises(ValueError, match="ready"):
        next_state(FileState.READY, FileEvent.DELETED_UPSTREAM, 1)


def test_illegal_transition_out_of_downloading_raises() -> None:
    with pytest.raises(ValueError, match="downloading"):
        next_state(FileState.DOWNLOADING, FileEvent.KEPT, 1)


def test_illegal_transition_from_a_terminal_state_raises() -> None:
    with pytest.raises(ValueError, match="illegal transition"):
        next_state(FileState.GONE, FileEvent.CLAIMED, 0)


def test_terminal_states_are_exactly_the_three_end_points() -> None:
    assert {FileState.KEPT, FileState.PASSED, FileState.GONE} == TERMINAL
    for state in TERMINAL:
        assert is_terminal(state)
    for state in CLAIMABLE:
        assert not is_terminal(state)
    assert not is_terminal(FileState.READY)
    assert not is_terminal(FileState.DOWNLOADING)
