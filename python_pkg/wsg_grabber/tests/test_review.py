"""Tests for the reviewer's behaviour.

Because every decision lives here rather than in the Tk module, the whole UI is
specified by these tests and none of them need a display.
"""

from __future__ import annotations

from python_pkg.wsg_grabber import review
from python_pkg.wsg_grabber.models import (
    Downloaded,
    Emptiness,
    FileReady,
    Indexed,
    ScanFinished,
    Verdict,
    WorkerFailed,
)
from python_pkg.wsg_grabber.tests.conftest import item as _item


def test_the_first_download_goes_straight_on_screen() -> None:
    """Watching starts as soon as one file lands, not when all of them do."""
    state = review.initial_state(indexed=9000, ready=[])
    assert state.current is None

    state = review.on_new_files(state, [_item("a")])
    assert state.current is not None
    assert state.current.md5 == "a-md5"
    assert state.pending == ()


def test_later_downloads_queue_behind_the_current_one() -> None:
    state = review.initial_state(9000, [_item("a")])
    state = review.on_new_files(state, [_item("b"), _item("c")])
    assert state.current is not None
    assert state.current.md5 == "a-md5"
    assert [item.md5 for item in state.pending] == ["b-md5", "c-md5"]


def test_new_files_with_nothing_to_add_is_a_no_op() -> None:
    state = review.initial_state(1, [_item("a")])
    assert review.on_new_files(state, []) is state


def test_a_previous_run_resumes_with_its_unreviewed_videos() -> None:
    state = review.initial_state(50, [_item("a"), _item("b")])
    assert state.current is not None
    assert state.current.md5 == "a-md5"
    assert len(state.pending) == 1


def test_keep_counts_and_advances() -> None:
    state = review.initial_state(2, [_item("a"), _item("b")])
    state = review.on_verdict(state, Verdict.KEEP)
    assert state.kept == 1
    assert state.passed == 0
    assert state.current is not None
    assert state.current.md5 == "b-md5"


def test_pass_counts_and_advances() -> None:
    state = review.initial_state(2, [_item("a"), _item("b")])
    state = review.on_verdict(state, Verdict.SKIP)
    assert state.passed == 1
    assert state.kept == 0
    assert state.current is not None
    assert state.current.md5 == "b-md5"


def test_the_last_verdict_empties_the_screen() -> None:
    state = review.initial_state(1, [_item("a")])
    state = review.on_verdict(state, Verdict.KEEP)
    assert state.current is None
    assert review.emptiness(state) is Emptiness.WAITING


def test_a_verdict_with_nothing_showing_is_ignored() -> None:
    state = review.initial_state(0, [])
    assert review.on_verdict(state, Verdict.KEEP) is state


def test_a_vanished_file_is_skipped() -> None:
    state = review.initial_state(2, [_item("a"), _item("b")])
    state = review.on_missing_locally(state)
    assert state.current is not None
    assert state.current.md5 == "b-md5"
    assert state.kept == 0
    assert state.passed == 0


def test_missing_with_nothing_showing_is_ignored() -> None:
    state = review.initial_state(0, [])
    assert review.on_missing_locally(state) is state


def test_events_fold_into_the_state() -> None:
    state = review.initial_state(0, [])
    state = review.on_event(state, Indexed(known=9028))
    assert state.indexed == 9028

    state = review.on_event(state, FileReady(item=_item("a")))
    assert state.current is not None

    state = review.on_event(state, Downloaded(count=7))
    assert state.downloaded == 7

    state = review.on_event(state, ScanFinished())
    assert state.scan_complete

    state = review.on_event(state, WorkerFailed(message="no route to host"))
    assert state.error == "no route to host"
