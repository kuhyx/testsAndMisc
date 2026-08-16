"""What the reviewer window requires of a video player.

Split out of :mod:`python_pkg.wsg_grabber.player` to keep it under the 250-line
cap. ``ui`` depends on this protocol rather than on :class:`~.player.MpvPlayer`,
so the window can be driven by a stub in the tests without mpv present.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from pathlib import Path


class Player(Protocol):
    """What the reviewer needs from a video player."""

    def play(self, path: Path) -> None:
        """Show *path*, replacing whatever is on screen.

        Args:
            path: Video file to play.
        """
        ...  # pragma: no cover

    def stop(self) -> None:
        """Blank the video area."""
        ...  # pragma: no cover

    def is_alive(self) -> bool:
        """Report whether the player is still running.

        Returns:
            bool: True while the process lives.
        """
        ...  # pragma: no cover

    def probe(self) -> dict[str, object]:
        """Report what the player is currently doing, for diagnostics.

        Returns:
            dict[str, object]: Property name to value.
        """
        ...  # pragma: no cover

    def close(self) -> None:
        """Shut the player down and release its resources."""
        ...  # pragma: no cover
