"""Tests for the review window when the queue runs dry."""

from __future__ import annotations

import queue
from typing import TYPE_CHECKING, cast
from unittest.mock import MagicMock, patch

import pytest

from python_pkg.wsg_grabber import review, ui
from python_pkg.wsg_grabber.models import (
    ReviewCommand,
    ReviewedItem,
    ReviewItem,
    Verdict,
)

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from python_pkg.wsg_grabber.models import DownloadEvent
    from python_pkg.wsg_grabber.review import SessionState


@pytest.fixture
def toolkit() -> Iterator[MagicMock]:
    """Replace tkinter in the ui module's namespace.

    Yields:
        MagicMock: The stand-in toolkit.
    """
    fake = MagicMock()
    # a fresh mock per widget, else status and filename are the same object
    fake.Frame.side_effect = lambda *_a, **_k: MagicMock()
    fake.Label.side_effect = lambda *_a, **_k: MagicMock()
    fake.Button.side_effect = lambda *_a, **_k: MagicMock()
    fake.BOTH = "both"
    fake.X = "x"
    fake.LEFT = "left"
    fake.RIGHT = "right"
    fake.BOTTOM = "bottom"
    with patch.object(ui, "tk", fake):
        yield fake


def _mock(widget: object) -> MagicMock:
    """View a mocked widget as the MagicMock it really is.

    The Widgets dataclass is typed with real Tk classes, so mypy will not let
    the tests reach ``call_args`` without this.

    Args:
        widget: The stand-in widget.

    Returns:
        MagicMock: The same object, typed for assertions.
    """
    return cast("MagicMock", widget)


def _item(tmp_path: Path, name: str = "a") -> ReviewItem:
    """Build a ReviewItem backed by a real file.

    Args:
        tmp_path: Per-test temporary directory.
        name: Distinguishes items.

    Returns:
        ReviewItem: Fixture value.
    """
    path = tmp_path / f"{name}.webm"
    path.write_bytes(b"video")
    return ReviewItem(
        md5=f"{name}-md5",
        path=path,
        orig_name=f"{name}.webm",
        fsize=5,
        width=4,
        height=3,
    )


def _callbacks() -> tuple[ui.Callbacks, MagicMock]:
    """Build callbacks that record what the window asked for.

    Returns:
        tuple: The callbacks and the recorder behind them.
    """
    recorder = MagicMock()
    _undone: dict[str, ReviewedItem | None] = {"item": None}

    def commit(state: SessionState, choice: Verdict) -> SessionState:
        recorder.commit(choice)
        if state.current is not None:
            _undone["item"] = ReviewedItem(
                item=state.current,
                choice=choice,
                reviewed_name=state.current.path.name,
            )
        return review.on_verdict(state, choice)

    def missing(state: SessionState) -> SessionState:
        recorder.missing()
        return review.on_missing_locally(state)

    def undo(state: SessionState) -> SessionState:
        recorder.undo()
        action = _undone["item"]
        if action is None or not review.can_undo(state):
            return state
        return review.on_undo(state, action)

    return (
        ui.Callbacks(
            commit=commit,
            missing=missing,
            undo=undo,
            shutdown=recorder.shutdown,
        ),
        recorder,
    )


def _window(
    state: SessionState,
    events: queue.SimpleQueue[DownloadEvent] | None = None,
) -> tuple[ui.ReviewWindow, MagicMock]:
    """Build a window over a mocked toolkit.

    Args:
        state: Starting state.
        events: Optional event queue.

    Returns:
        tuple: The window and the callback recorder.
    """
    callbacks, recorder = _callbacks()
    window = ui.ReviewWindow(state, events or queue.SimpleQueue(), callbacks)
    return window, recorder


def test_apply_stops_and_disables_when_idle(toolkit: MagicMock) -> None:
    window, _ = _window(review.initial_state(0, []))
    player = MagicMock()
    window.attach_player(player)
    window.apply(
        ReviewCommand(
            play=None,
            stop=True,
            status="s",
            title="t",
            filename="f",
            verdicts_enabled=False,
            undo_enabled=False,
            quit_app=False,
        ),
    )
    # nothing was playing, so there is nothing to stop; the buttons still go dead
    player.stop.assert_not_called()
    _mock(window.widgets.keep).configure.assert_called_with(state="disabled")


def test_apply_quits_when_told_to(toolkit: MagicMock) -> None:
    window, recorder = _window(review.initial_state(0, []))
    window.apply(
        ReviewCommand(
            play=None,
            stop=False,
            status="s",
            title="t",
            filename="f",
            verdicts_enabled=False,
            undo_enabled=False,
            quit_app=True,
        ),
    )
    recorder.shutdown.assert_called_once()


def test_playing_without_a_player_is_a_no_op(
    toolkit: MagicMock,
    tmp_path: Path,
) -> None:
    window, _ = _window(review.initial_state(1, [_item(tmp_path)]))
    window.refresh()


def test_a_video_that_vanished_is_skipped(
    toolkit: MagicMock,
    tmp_path: Path,
) -> None:
    """A file can disappear between download and review; don't hang on it."""
    first = _item(tmp_path, "a")
    state = review.initial_state(2, [first, _item(tmp_path, "b")])
    window, recorder = _window(state)
    first.path.unlink()
    player = MagicMock()
    window.attach_player(player)

    recorder.missing.assert_called_once()
    assert window.state.current is not None
    assert window.state.current.md5 == "b-md5"
