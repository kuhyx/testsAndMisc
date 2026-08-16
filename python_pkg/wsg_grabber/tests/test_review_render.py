"""Tests for what the reviewer puts on screen.

Split from ``test_review.py`` to keep every file under the 250-line cap; these
cover the pure state-to-text functions that now live in ``review._render``.
"""

from __future__ import annotations

from pathlib import Path

from python_pkg.wsg_grabber import review
from python_pkg.wsg_grabber.models import (
    Downloaded,
    Emptiness,
    ScanFinished,
    Verdict,
    WorkerFailed,
)
from python_pkg.wsg_grabber.tests.conftest import item as _item


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
