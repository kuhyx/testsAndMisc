"""The only code in this package that moves bytes around on disk.

Deliberately tiny, because everything interesting about a verdict was already
decided in :mod:`python_pkg.wsg_grabber.verdict`. There is no ``unlink`` here:
a passed video is relocated to ``trash/`` and stays there until the user
removes it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from python_pkg.wsg_grabber import logs

if TYPE_CHECKING:
    from pathlib import Path

    from python_pkg.wsg_grabber.models import FileMove


def existing_names(directory: Path) -> set[str]:
    """Return the filenames already present in *directory*.

    Args:
        directory: Directory to inspect; need not exist.

    Returns:
        set[str]: Names currently in the directory.
    """
    if not directory.is_dir():
        return set()
    return {entry.name for entry in directory.iterdir()}


def apply_move(move: FileMove) -> bool:
    """Carry out a planned relocation.

    Refuses to overwrite an existing destination. ``Path.replace`` clobbers
    silently, so without this check a caller that forgot to pick a
    collision-free name would destroy a video the user had already decided to
    keep -- exactly the thing this package promises never to do. Callers pick
    the name with :func:`verdict.unique_destination`; this is the backstop that
    makes the guarantee structural rather than a convention.

    Args:
        move: Where the file is and where it should go.

    Returns:
        bool: True when the file was moved. False when the source had already
        vanished, or when the destination is occupied -- the caller treats
        either as "this file is not where I thought", never as success.
    """
    if not move.src.exists():
        return False
    if move.dst.exists():
        logs.error(
            "files.destination_occupied",
            src=str(move.src),
            dst=str(move.dst),
        )
        return False
    move.dst.parent.mkdir(parents=True, exist_ok=True)
    move.src.replace(move.dst)
    return True
