"""The Tk window: video on top, keep/pass bar underneath.

The only module in this package that imports ``tkinter``. Almost every callback
hands off to :mod:`python_pkg.wsg_grabber.review`, gets a
:class:`ReviewCommand` back and applies it verbatim, so the behaviour is
specified and covered without a display ever being opened.

Two decisions do live here, both because a bug proved they had to: ``_play``
skips a reload when the file is already playing, and drops an item whose file
has vanished. Everything else is wiring.

The control bar sits *below* the video rather than over it: with ``--wid`` mpv
reparents its own child window onto the frame and covers it completely, so a
widget drawn on top would be hidden.

Nothing here tracks the window size. mpv resizes itself to fill the frame it was
given, and telling it otherwise via ``geometry`` leaves the video drawn at the
wrong size -- which is exactly what happened the first time this ran.
"""

from __future__ import annotations

from dataclasses import dataclass
import tkinter as tk
from typing import TYPE_CHECKING

from python_pkg.wsg_grabber import logs
from python_pkg.wsg_grabber._display import DisplayMixin
from python_pkg.wsg_grabber.constants import (
    CONTROL_BAR_HEIGHT_PX,
    KEEP_KEYS,
    PASS_KEYS,
    QUIT_KEYS,
    UNDO_KEYS,
    WINDOW_HEIGHT_PX,
    WINDOW_WIDTH_PX,
)
from python_pkg.wsg_grabber.models import Verdict

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path
    import queue

    from python_pkg.wsg_grabber.models import DownloadEvent
    from python_pkg.wsg_grabber.player import Player
    from python_pkg.wsg_grabber.review import SessionState

_BACKGROUND = "#1B1D21"
_ACCENT = "#B8862E"
_TEXT = "#E8E6E3"


@dataclass(frozen=True, slots=True)
class Callbacks:
    """What the window asks the rest of the application to do."""

    commit: Callable[[SessionState, Verdict], SessionState]
    missing: Callable[[SessionState], SessionState]
    undo: Callable[[SessionState], SessionState]
    shutdown: Callable[[], None]


@dataclass
class Widgets:
    """The widgets, grouped so the window stays within the attribute limit."""

    root: tk.Tk
    video: tk.Frame
    status: tk.Label
    filename: tk.Label
    keep: tk.Button
    skip: tk.Button
    undo: tk.Button


class ReviewWindow(DisplayMixin):
    """Presents downloaded videos one at a time for a keep/pass decision.

    The screen-updating and state-transition halves live in _display to keep
    this module under the 250-line cap. Widget construction stays here: this
    is the only module that imports tkinter, and the tests fake the toolkit
    by patching ``ui.tk``.
    """

    def __init__(
        self,
        state: SessionState,
        events: queue.SimpleQueue[DownloadEvent],
        callbacks: Callbacks,
    ) -> None:
        """Build the window.

        The player is attached afterwards with :meth:`attach_player`, because
        it needs the X11 id of a frame that must exist first.

        Args:
            state: Starting session state.
            events: Queue the download worker publishes to.
            callbacks: Hooks back into the application.
        """
        self._state = state
        self._events = events
        self._callbacks = callbacks
        self._player: Player | None = None
        self._after_id: str | None = None
        self._playing: Path | None = None
        self._widgets = self._build()
        self._bind_keys()

    @property
    def widgets(self) -> Widgets:
        """Return the constructed widgets.

        Returns:
            Widgets: The window's parts.
        """
        return self._widgets

    @property
    def state(self) -> SessionState:
        """Return the current session state.

        Returns:
            SessionState: What the window is showing.
        """
        return self._state

    def _build(self) -> Widgets:
        """Construct the window and its widgets.

        Returns:
            Widgets: The constructed parts.
        """
        root = tk.Tk()
        root.title("/wsg/")
        root.geometry(f"{WINDOW_WIDTH_PX}x{WINDOW_HEIGHT_PX}")
        root.configure(bg=_BACKGROUND)

        video = tk.Frame(root, bg="black")
        video.pack(fill=tk.BOTH, expand=True)

        controls = tk.Frame(root, bg=_BACKGROUND, height=CONTROL_BAR_HEIGHT_PX)
        controls.pack(fill=tk.X, side=tk.BOTTOM)

        keep = tk.Button(
            controls,
            text="✔  KEEP  (k)",
            bg=_ACCENT,
            fg=_BACKGROUND,
            command=self.on_keep,
        )
        keep.pack(side=tk.LEFT, padx=16, pady=10)

        skip = tk.Button(
            controls,
            text="✘  PASS  (j)",
            bg=_BACKGROUND,
            fg=_TEXT,
            command=self.on_pass,
        )
        skip.pack(side=tk.RIGHT, padx=16, pady=10)

        undo = tk.Button(
            controls,
            text="↶  UNDO  (u)",
            bg=_BACKGROUND,
            fg=_TEXT,
            command=self.on_undo,
        )
        undo.pack(side=tk.LEFT, padx=8, pady=10)

        status = tk.Label(controls, text="", bg=_BACKGROUND, fg=_ACCENT)
        status.pack()
        filename = tk.Label(controls, text="", bg=_BACKGROUND, fg=_TEXT)
        filename.pack()

        root.protocol("WM_DELETE_WINDOW", self.on_quit)
        return Widgets(
            root=root,
            video=video,
            status=status,
            filename=filename,
            keep=keep,
            skip=skip,
            undo=undo,
        )

    def _bind_keys(self) -> None:
        """Bind the keyboard shortcuts onto the toplevel."""
        for sequence in KEEP_KEYS:
            self._widgets.root.bind(sequence, lambda _event: self.on_keep())
        for sequence in PASS_KEYS:
            self._widgets.root.bind(sequence, lambda _event: self.on_pass())
        for sequence in UNDO_KEYS:
            self._widgets.root.bind(sequence, lambda _event: self.on_undo())
        for sequence in QUIT_KEYS:
            self._widgets.root.bind(sequence, lambda _event: self.on_quit())

    def video_wid(self) -> int:
        """Return the X11 id of the video frame.

        Returns:
            int: Window id to hand to mpv's ``--wid``.
        """
        self._widgets.root.update()
        return int(self._widgets.video.winfo_id())

    def on_keep(self) -> None:
        """Keep the current video."""
        self._verdict(Verdict.KEEP)

    def on_pass(self) -> None:
        """Pass on the current video."""
        self._verdict(Verdict.SKIP)

    def shutdown(self) -> None:
        """Cancel the tick, stop the worker and destroy the window."""
        logs.event(
            "review.shutdown",
            kept=self._state.kept,
            passed=self._state.passed,
            queued=len(self._state.pending),
        )
        try:
            if self._after_id is not None:
                self._widgets.root.after_cancel(self._after_id)
                self._after_id = None
            self._callbacks.shutdown()
            player, self._player = self._player, None
            if player is not None:
                player.close()
        finally:
            # Whatever failed above -- a Ctrl-C landing in the worker join, an
            # mpv that will not die -- the window must not be left up and
            # frozen with its tick already cancelled.
            self._widgets.root.destroy()

    def run(self) -> None:
        """Start ticking and hand control to Tk."""
        self.tick()
        self._widgets.root.mainloop()
