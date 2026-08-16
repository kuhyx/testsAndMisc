"""Applying a rendered command to the screen.

Split out of :mod:`python_pkg.wsg_grabber.ui` to keep it under the 250-line
cap. Note what is *not* here: creating widgets. ``ui`` is the only module that
imports ``tkinter``, and ``test_ui.py`` fakes the toolkit with
``patch.object(ui, "tk", ...)``, so construction has to stay there. These two
methods only ever reach widgets through ``self._widgets``, so they move freely.

A mixin rather than free functions because both read and write the window's
playback bookkeeping and ``apply`` is part of ReviewWindow's public surface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from python_pkg.wsg_grabber import logs, review
from python_pkg.wsg_grabber.constants import POLL_INTERVAL_MS

if TYPE_CHECKING:
    from pathlib import Path
    import queue

    from python_pkg.wsg_grabber._callbacks import Callbacks
    from python_pkg.wsg_grabber.models import (
        DownloadEvent,
        ReviewCommand,
        Verdict,
    )
    from python_pkg.wsg_grabber.player import Player
    from python_pkg.wsg_grabber.review import SessionState
    from python_pkg.wsg_grabber.ui import Widgets


class DisplayMixin(ABC):
    """The screen-updating half of :class:`~.ui.ReviewWindow`."""

    _widgets: Widgets
    _callbacks: Callbacks
    _player: Player | None
    _playing: Path | None
    _state: SessionState
    _after_id: str | None
    _events: queue.SimpleQueue[DownloadEvent]

    @abstractmethod
    def shutdown(self) -> None:
        """Close the player and tear the window down."""

    def apply(self, command: ReviewCommand) -> None:
        """Carry out a rendered command.

        Args:
            command: What to show and do.
        """
        if command.play is not None:
            self._play(command.play)
        if command.stop and self._player is not None and self._playing is not None:
            self._playing = None
            self._player.stop()
        self._widgets.status.configure(text=command.status)
        self._widgets.filename.configure(text=command.filename)
        self._widgets.root.title(command.title)
        if command.verdicts_enabled:
            self._widgets.keep.configure(state="normal")
            self._widgets.skip.configure(state="normal")
        else:
            self._widgets.keep.configure(state="disabled")
            self._widgets.skip.configure(state="disabled")
        if command.undo_enabled:
            self._widgets.undo.configure(state="normal")
        else:
            self._widgets.undo.configure(state="disabled")
        if command.quit_app:
            self.shutdown()

    def _play(self, path: Path) -> None:
        """Show a video, unless it is already the one playing.

        The already-playing guard is essential rather than an optimisation:
        ``refresh`` runs on every tick, so without it ``loadfile`` would be sent
        several times a second and the video would restart continuously instead
        of ever playing.

        A file can also vanish between being downloaded and being reviewed.
        Handing mpv a dead path would leave the reviewer stuck on a black
        frame, so the item is dropped and the next one shown instead.

        Args:
            path: Video to play.
        """
        if self._player is None:
            logs.debug("review.play_skipped", reason="no player", file=path.name)
            return
        if path == self._playing:
            logs.debug("review.play_skipped", reason="already playing", file=path.name)
            return
        if not path.exists():
            logs.warning("review.file_missing", file=path.name, path=str(path))
            self._state = self._callbacks.missing(self._state)
            self.refresh()
            return
        # Recorded BEFORE the new load, so a frozen-looking session shows what
        # mpv was doing with the file it was supposedly already playing.
        logs.event(
            "review.show",
            file=path.name,
            previous=self._playing.name if self._playing else None,
            player_alive=self._player.is_alive(),
            mpv_before=self._player.probe(),
        )
        self._playing = path
        self._player.play(path)

    def _verdict(self, choice: Verdict) -> None:
        """Apply a verdict and redraw.

        Args:
            choice: What the user decided.
        """
        before = self._state.current
        self._state = self._callbacks.commit(self._state, choice)
        after = self._state.current
        logs.event(
            "review.verdict",
            choice=choice.value,
            on=before.orig_name if before else None,
            on_file=before.path.name if before else None,
            next_file=after.path.name if after else None,
            queued=len(self._state.pending),
            kept=self._state.kept,
            passed=self._state.passed,
        )
        self.refresh()

    def on_undo(self) -> None:
        """Take back the last verdict and show that video again."""
        before = self._state.current
        self._state = self._callbacks.undo(self._state)
        after = self._state.current
        logs.event(
            "review.undo",
            was_showing=before.orig_name if before else None,
            now_showing=after.orig_name if after else None,
            kept=self._state.kept,
            passed=self._state.passed,
            remaining_undos=self._state.undoable,
        )
        self.refresh()

    def on_quit(self) -> None:
        """Begin shutting down."""
        self._state = review.on_quit(self._state)
        self.refresh()

    def tick(self) -> None:
        """Drain the worker's events, redraw, and schedule the next tick."""
        self.drain()
        self.refresh()
        self._after_id = self._widgets.root.after(POLL_INTERVAL_MS, self.tick)

    def drain(self) -> None:
        """Fold every queued worker event into the session state."""
        while not self._events.empty():
            self._state = review.on_event(self._state, self._events.get_nowait())

    def refresh(self) -> None:
        """Re-render from the current state."""
        self.apply(review.render(self._state))

    def attach_player(self, player: Player) -> None:
        """Adopt a player and show the first video.

        Args:
            player: The video player to drive.
        """
        self._player = player
        self.refresh()
