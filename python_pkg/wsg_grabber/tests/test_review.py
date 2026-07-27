"""Tests for the reviewer's behaviour.

Because every decision lives here rather than in the Tk module, the whole UI is
specified by these tests and none of them need a display.
"""

from __future__ import annotations

from pathlib import Path

from python_pkg.wsg_grabber import review
from python_pkg.wsg_grabber.models import (
    Downloaded,
    Emptiness,
    FileReady,
    Indexed,
    ReviewedItem,
    ReviewItem,
    ScanFinished,
    Verdict,
    WorkerFailed,
)


def _item(name: str = "a") -> ReviewItem:
    """Build a ReviewItem.

    Args:
        name: Distinguishes items within a test.

    Returns:
        ReviewItem: Fixture value.
    """
    return ReviewItem(
        md5=f"{name}-md5",
        path=Path(f"/incoming/{name}.webm"),
        orig_name=f"{name}.webm",
        fsize=2 * 1024 * 1024,
        width=480,
        height=360,
    )


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


def test_emptiness_distinguishes_waiting_from_exhausted() -> None:
    state = review.initial_state(0, [])
    assert review.emptiness(state) is Emptiness.WAITING

    state = review.on_event(state, ScanFinished())
    assert review.emptiness(state) is Emptiness.EXHAUSTED

    state = review.on_new_files(state, [_item("a")])
    assert review.emptiness(state) is Emptiness.NOT_EMPTY


def test_status_line_reports_progress() -> None:
    state = review.initial_state(9028, [_item("a")])
    state = review.on_event(state, Downloaded(count=12))
    state = review.on_verdict(state, Verdict.KEEP)
    line = review.status_line(state)
    assert "kept 1" in line
    assert "passed 0" in line
    assert "downloaded 12/9028" in line


def test_status_line_omits_the_total_before_indexing() -> None:
    state = review.initial_state(0, [_item("a")])
    assert "/0" not in review.status_line(state)


def test_status_line_shows_the_two_empty_moods() -> None:
    state = review.initial_state(0, [])
    assert "waiting for downloads" in review.status_line(state)
    assert "all caught up" in review.status_line(
        review.on_event(state, ScanFinished()),
    )


def test_a_worker_failure_takes_over_the_status_line() -> None:
    state = review.on_event(review.initial_state(0, []), WorkerFailed(message="boom"))
    assert review.status_line(state) == "downloader stopped: boom"


def test_filename_line_describes_the_current_video() -> None:
    state = review.initial_state(1, [_item("a")])
    line = review.filename_line(state)
    assert "a.webm" in line
    assert "480x360" in line
    assert "2.0 MiB" in line


def test_filename_line_has_a_placeholder_when_idle() -> None:
    assert review.filename_line(review.initial_state(0, [])) == "—"


def test_title_line_carries_the_tally() -> None:
    state = review.initial_state(1, [_item("a")])
    state = review.on_verdict(state, Verdict.KEEP)
    assert review.title_line(state) == "/wsg/ — kept 1, passed 0"


def test_render_drives_the_window_completely() -> None:
    state = review.initial_state(5, [_item("a")])
    command = review.render(state)
    assert command.play == Path("/incoming/a.webm")
    assert not command.stop
    assert command.verdicts_enabled
    assert not command.quit_app
    assert command.status == review.status_line(state)
    assert command.title == review.title_line(state)
    assert command.filename == review.filename_line(state)


def test_render_stops_playback_when_nothing_is_queued() -> None:
    command = review.render(review.initial_state(0, []))
    assert command.play is None
    assert command.stop
    assert not command.verdicts_enabled


def test_render_signals_quit_and_disables_the_buttons() -> None:
    state = review.on_quit(review.initial_state(1, [_item("a")]))
    command = review.render(state)
    assert command.quit_app
    assert not command.verdicts_enabled


def _reviewed(item: ReviewItem, choice: Verdict = Verdict.SKIP) -> ReviewedItem:
    """Build the record a verdict would have persisted.

    Args:
        item: The reviewed video.
        choice: What was decided.

    Returns:
        ReviewedItem: Reversible verdict.
    """
    return ReviewedItem(item=item, choice=choice, reviewed_name=item.path.name)


def test_undo_availability_comes_from_the_index_not_memory() -> None:
    """The count is seeded from the index, so undo survives a restart."""
    resumed = review.initial_state(5, [_item("a")], undoable=3)
    assert review.can_undo(resumed)
    assert "u undoes (3)" in review.status_line(resumed)
    assert not review.can_undo(review.initial_state(5, [_item("a")]))


def test_a_recorded_verdict_can_be_undone() -> None:
    first = _item("a")
    state = review.initial_state(2, [first, _item("b")])
    state = review.on_verdict(state, Verdict.SKIP)
    assert review.can_undo(state)

    state = review.on_undo(state, _reviewed(first))
    assert state.current is not None
    assert state.current.md5 == "a-md5"
    assert state.passed == 0
    assert [item.md5 for item in state.pending] == ["b-md5"]
    assert not review.can_undo(state)


def test_undo_restores_the_keep_counter() -> None:
    first = _item("a")
    state = review.initial_state(1, [first])
    state = review.on_verdict(state, Verdict.KEEP)
    assert state.kept == 1
    assert review.on_undo(state, _reviewed(first, Verdict.KEEP)).kept == 0


def test_undo_works_when_the_queue_has_run_dry() -> None:
    first = _item("a")
    state = review.initial_state(1, [first])
    state = review.on_verdict(state, Verdict.SKIP)
    assert state.current is None
    state = review.on_undo(state, _reviewed(first))
    assert state.current is not None
    assert state.current.md5 == "a-md5"


def test_forget_last_drops_one_undo_without_restoring() -> None:
    first = _item("a")
    state = review.initial_state(1, [first])
    state = review.on_verdict(state, Verdict.SKIP)
    dropped = review.forget_last(state)
    assert not review.can_undo(dropped)
    assert dropped.passed == 1
    assert review.forget_last(dropped).undoable == 0


def test_the_status_line_advertises_undo_once_it_is_possible() -> None:
    first = _item("a")
    state = review.initial_state(1, [first])
    assert "u undoes" not in review.status_line(state)
    state = review.on_verdict(state, Verdict.SKIP)
    assert "u undoes (1)" in review.status_line(state)


def test_render_enables_undo_only_when_something_can_be_undone() -> None:
    first = _item("a")
    state = review.initial_state(1, [first])
    assert not review.render(state).undo_enabled
    state = review.on_verdict(state, Verdict.KEEP)
    assert review.render(state).undo_enabled
    assert not review.render(review.on_quit(state)).undo_enabled
