"""Tests for the window's event-drain tick and shutdown."""

from __future__ import annotations

import queue
from typing import TYPE_CHECKING, cast
from unittest.mock import MagicMock, patch

import pytest

from python_pkg.wsg_grabber import review, ui
from python_pkg.wsg_grabber.constants import (
    UNDO_KEYS,
)
from python_pkg.wsg_grabber.models import (
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


def test_tick_drains_events_and_reschedules(toolkit: MagicMock) -> None:
    from python_pkg.wsg_grabber.models import Indexed

    events: queue.SimpleQueue[DownloadEvent] = queue.SimpleQueue()
    events.put(Indexed(known=42))
    window, _ = _window(review.initial_state(0, []), events)
    window.tick()
    assert window.state.indexed == 42
    _mock(window.widgets.root).after.assert_called_once()
    assert _mock(window.widgets.root).after.call_args.args[1] == window.tick


def test_drain_on_an_empty_queue_is_harmless(toolkit: MagicMock) -> None:
    window, _ = _window(review.initial_state(0, []))
    window.drain()
    assert window.state.indexed == 0


def test_shutdown_cancels_the_tick_and_closes_the_player(
    toolkit: MagicMock,
) -> None:
    """A leaked after-callback or an orphan mpv would outlive the window."""
    window, recorder = _window(review.initial_state(0, []))
    player = MagicMock()
    window.attach_player(player)
    window.tick()
    window.shutdown()
    _mock(window.widgets.root).after_cancel.assert_called_once()
    player.close.assert_called_once()
    recorder.shutdown.assert_called_once()
    _mock(window.widgets.root).destroy.assert_called_once()


def test_shutdown_without_a_pending_tick(toolkit: MagicMock) -> None:
    window, _ = _window(review.initial_state(0, []))
    window.shutdown()
    _mock(window.widgets.root).after_cancel.assert_not_called()


def test_video_wid_realises_the_window_first(toolkit: MagicMock) -> None:
    window, _ = _window(review.initial_state(0, []))
    _mock(window.widgets.video).winfo_id.return_value = 4321
    assert window.video_wid() == 4321
    _mock(window.widgets.root).update.assert_called()


def test_run_starts_ticking_then_enters_the_loop(toolkit: MagicMock) -> None:
    window, _ = _window(review.initial_state(0, []))
    window.run()
    _mock(window.widgets.root).mainloop.assert_called_once()
    _mock(window.widgets.root).after.assert_called_once()


def test_undo_takes_back_the_last_verdict(
    toolkit: MagicMock,
    tmp_path: Path,
) -> None:
    """The misclick case: passed something you meant to keep."""
    state = review.initial_state(2, [_item(tmp_path, "a"), _item(tmp_path, "b")])
    window, recorder = _window(state)
    player = MagicMock()
    window.attach_player(player)

    window.on_pass()
    assert window.state.current is not None
    assert window.state.current.md5 == "b-md5"
    assert window.state.passed == 1

    window.on_undo()
    recorder.undo.assert_called_once()
    assert window.state.current is not None
    assert window.state.current.md5 == "a-md5"
    assert window.state.passed == 0
    # and the video that was on screen is not lost
    assert [item.md5 for item in window.state.pending] == ["b-md5"]


def test_the_undo_shortcut_is_wired(toolkit: MagicMock, tmp_path: Path) -> None:
    state = review.initial_state(1, [_item(tmp_path)])
    window, recorder = _window(state)
    window.attach_player(MagicMock())
    window.on_keep()
    bound = _mock(window.widgets.root).bind.call_args_list
    handlers = {call.args[0]: call.args[1] for call in bound}
    handlers[UNDO_KEYS[0]](object())
    recorder.undo.assert_called_once()


def test_the_undo_button_is_disabled_until_there_is_something_to_undo(
    toolkit: MagicMock,
    tmp_path: Path,
) -> None:
    state = review.initial_state(1, [_item(tmp_path)])
    window, _ = _window(state)
    window.attach_player(MagicMock())
    assert _mock(window.widgets.undo).configure.call_args.kwargs["state"] == "disabled"
    window.on_keep()
    assert _mock(window.widgets.undo).configure.call_args.kwargs["state"] == "normal"
