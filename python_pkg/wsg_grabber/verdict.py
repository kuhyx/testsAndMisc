"""What a keep/pass decision means, expressed as data.

Planning a move and performing it are split deliberately: everything here is
pure and exhaustively testable, and :mod:`python_pkg.wsg_grabber.files` is the
only code that touches the filesystem.

Nothing in this package deletes a video. A pass relocates it to ``trash/`` and
leaves clearing that directory to the user.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from python_pkg.wsg_grabber.models import FileMove, Verdict
from python_pkg.wsg_grabber.states import FileState

if TYPE_CHECKING:
    from collections.abc import Container
    from pathlib import Path

    from python_pkg.wsg_grabber.models import ReviewItem


def target_state(choice: Verdict) -> FileState:
    """Return the terminal state a verdict leads to.

    Args:
        choice: The user's decision.

    Returns:
        FileState: ``KEPT`` or ``PASSED``.
    """
    return FileState.KEPT if choice is Verdict.KEEP else FileState.PASSED


def target_dir(choice: Verdict, keep: Path, trash: Path) -> Path:
    """Return the directory a verdict sends a file to.

    Args:
        choice: The user's decision.
        keep: Directory for kept videos.
        trash: Directory for passed videos.

    Returns:
        Path: Destination directory.
    """
    return keep if choice is Verdict.KEEP else trash


def unique_destination(directory: Path, name: str, taken: Container[str]) -> Path:
    """Return a collision-free destination inside *directory*.

    ``taken`` is supplied by the caller rather than read from disk, keeping this
    function pure and its collision handling directly testable.

    Args:
        directory: Destination directory.
        name: Preferred filename.
        taken: Names already present.

    Returns:
        Path: A path whose name is not in *taken*.
    """
    if name not in taken:
        return directory / name
    stem, _, suffix = name.rpartition(".")
    base, ext = (stem, f".{suffix}") if stem else (name, "")
    index = 2
    while f"{base}-{index}{ext}" in taken:
        index += 1
    return directory / f"{base}-{index}{ext}"


def plan_move(
    item: ReviewItem,
    choice: Verdict,
    keep: Path,
    trash: Path,
    taken: Container[str] = (),
) -> FileMove:
    """Work out where a reviewed video should end up.

    Args:
        item: The video under review.
        choice: The user's decision.
        keep: Directory for kept videos.
        trash: Directory for passed videos.
        taken: Names already used in the destination directory.

    Returns:
        FileMove: Source, destination and the file's identity.
    """
    destination = target_dir(choice, keep, trash)
    return FileMove(
        md5=item.md5,
        src=item.path,
        dst=unique_destination(destination, item.path.name, taken),
    )
