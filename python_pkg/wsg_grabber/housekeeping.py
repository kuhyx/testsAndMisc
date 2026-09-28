"""What the session does around a verdict besides the verdict itself.

Kept out of :mod:`python_pkg.wsg_grabber.app` so that module stays about
composition and shutdown: migrating the old ``keep/`` directory, pruning
``trash/``, and working out where a kept file actually is when undo asks.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from python_pkg.wsg_grabber import paths
from python_pkg.wsg_grabber._migrate_keep import migrate_keep
from python_pkg.wsg_grabber._prune import prune_trash
from python_pkg.wsg_grabber.models import Verdict

if TYPE_CHECKING:
    from pathlib import Path
    import sqlite3

    from python_pkg.wsg_grabber.models import ReviewedItem


def on_startup(conn: sqlite3.Connection) -> None:
    """Bring the on-disk layout in line with the index before reviewing.

    Args:
        conn: Open connection.
    """
    migrate_keep(conn)
    prune_trash(conn)


def after_verdict(conn: sqlite3.Connection, choice: Verdict) -> None:
    """Keep ``trash/`` at its cap once a pass has landed there.

    Args:
        conn: Open connection.
        choice: The verdict just recorded.
    """
    if choice is not Verdict.KEEP:
        prune_trash(conn)


def locate_reviewed(action: ReviewedItem) -> Path:
    """Return where the file a verdict moved is sitting now.

    A pass has exactly one home. A keep may be in this year's cloud folder,
    last year's, ``~/Downloads``, wherever the media sync swept it, or the
    legacy ``keep/`` -- the first candidate that holds the name wins, and when
    none does the current keep dir is returned so the caller's move fails
    visibly rather than silently.

    Args:
        action: The verdict being undone.

    Returns:
        Path: Expected location of the file.
    """
    if action.choice is not Verdict.KEEP:
        return paths.trash_dir() / action.reviewed_name
    for directory in paths.kept_candidates():
        candidate = directory / action.reviewed_name
        if candidate.is_file():
            return candidate
    return paths.keep_dir() / action.reviewed_name
