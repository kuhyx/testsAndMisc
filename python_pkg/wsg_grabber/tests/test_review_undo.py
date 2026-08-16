"""Tests for taking a verdict back.

Split from ``test_review.py`` to keep every file under the 250-line cap; these
cover the group that now lives in ``review._undo``.
"""

from __future__ import annotations

from python_pkg.wsg_grabber import review
from python_pkg.wsg_grabber.models import Verdict
from python_pkg.wsg_grabber.tests.conftest import item as _item
from python_pkg.wsg_grabber.tests.conftest import reviewed as _reviewed


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
