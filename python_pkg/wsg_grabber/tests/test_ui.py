"""Tests for the Tk window.

``tkinter`` is replaced wholesale in the module's namespace, so every widget is
a mock and no real ``Tk()`` is ever constructed. That matters beyond speed: CI
has no display, and instantiating Tk there would fail outright.

There is deliberately little to test here, because the window contains no
decisions -- those all live in ``review`` and are covered by ``test_review``.
"""

from __future__ import annotations

import queue
from typing import TYPE_CHECKING, cast
from unittest.mock import MagicMock, patch

import pytest

from python_pkg.wsg_grabber import review, ui
from python_pkg.wsg_grabber.constants import (
    KEEP_KEYS,
    PASS_KEYS,
    QUIT_KEYS,
    UNDO_KEYS,
)
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


def test_the_window_has_a_video_area_and_a_control_bar(toolkit: MagicMock) -> None:
    window, _ = _window(review.initial_state(0, []))
    assert toolkit.Tk.called
    assert toolkit.Button.call_count == 3  # keep, pass, undo
    # two frames: the video area and the control bar below it
    assert toolkit.Frame.call_count == 2
    # the video area expands; the bar sits under it rather than over it, because
    # mpv's --wid child window covers whatever shares its frame
    assert _mock(window.widgets.video).pack.call_args.kwargs["expand"]


def test_every_shortcut_is_bound(toolkit: MagicMock) -> None:
    window, _ = _window(review.initial_state(0, []))
    calls = _mock(window.widgets.root).bind.call_args_list
    bound = {call.args[0] for call in calls}
    assert set(KEEP_KEYS) <= bound
    assert set(PASS_KEYS) <= bound
    assert set(QUIT_KEYS) <= bound
    assert set(UNDO_KEYS) <= bound


def test_keep_and_pass_shortcuts_reach_the_callbacks(
    toolkit: MagicMock,
    tmp_path: Path,
) -> None:
    state = review.initial_state(2, [_item(tmp_path, "a"), _item(tmp_path, "b")])
    window, recorder = _window(state)
    window.attach_player(MagicMock())

    bound = _mock(window.widgets.root).bind.call_args_list
    handlers = {call.args[0]: call.args[1] for call in bound}
    handlers[KEEP_KEYS[0]](object())
    first: object = recorder.commit.call_args.args[0]
    assert first is Verdict.KEEP
    handlers[PASS_KEYS[0]](object())
    second: object = recorder.commit.call_args.args[0]
    assert second is Verdict.SKIP


def test_the_quit_shortcut_shuts_down(toolkit: MagicMock) -> None:
    window, recorder = _window(review.initial_state(0, []))
    bound = _mock(window.widgets.root).bind.call_args_list
    handlers = {call.args[0]: call.args[1] for call in bound}
    handlers[QUIT_KEYS[0]](object())
    recorder.shutdown.assert_called_once()
    _mock(window.widgets.root).destroy.assert_called_once()


def test_the_buttons_call_the_same_handlers(
    toolkit: MagicMock,
    tmp_path: Path,
) -> None:
    state = review.initial_state(1, [_item(tmp_path)])
    window, recorder = _window(state)
    window.attach_player(MagicMock())
    window.on_keep()
    assert recorder.commit.call_args.args[0] is Verdict.KEEP


def test_apply_plays_and_labels(toolkit: MagicMock, tmp_path: Path) -> None:
    window, _ = _window(review.initial_state(0, []))
    player = MagicMock()
    window.attach_player(player)
    path = tmp_path / "x.webm"
    path.write_bytes(b"v")

    window.apply(
        ReviewCommand(
            play=path,
            stop=False,
            status="status text",
            title="title text",
            filename="file text",
            verdicts_enabled=True,
            undo_enabled=False,
            quit_app=False,
        ),
    )
    player.play.assert_called_once_with(path)
    _mock(window.widgets.status).configure.assert_called_with(text="status text")
    _mock(window.widgets.filename).configure.assert_called_with(text="file text")
    _mock(window.widgets.root).title.assert_called_with("title text")
    _mock(window.widgets.keep).configure.assert_called_with(state="normal")


def test_the_same_video_is_only_loaded_once(
    toolkit: MagicMock,
    tmp_path: Path,
) -> None:
    """refresh() runs every tick; re-sending loadfile restarts the video."""
    window, _ = _window(review.initial_state(1, [_item(tmp_path)]))
    player = MagicMock()
    window.attach_player(player)
    assert player.play.call_count == 1

    for _ in range(10):
        window.tick()
    assert player.play.call_count == 1


def test_advancing_loads_the_next_video(toolkit: MagicMock, tmp_path: Path) -> None:
    state = review.initial_state(2, [_item(tmp_path, "a"), _item(tmp_path, "b")])
    window, _ = _window(state)
    player = MagicMock()
    window.attach_player(player)
    window.on_keep()
    assert player.play.call_count == 2
    assert player.play.call_args.args[0].name == "b.webm"


def test_stopping_lets_the_same_video_load_again(
    toolkit: MagicMock,
    tmp_path: Path,
) -> None:
    item = _item(tmp_path)
    window, _ = _window(review.initial_state(1, [item]))
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
    player.stop.assert_called_once()
    window.refresh()
    assert player.play.call_count == 2


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
