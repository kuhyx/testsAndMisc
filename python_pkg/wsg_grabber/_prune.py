"""Keeping ``trash/`` bounded.

A pass used to be a move into a directory nobody ever emptied; 23k files and
77 GB later that was clearly wrong. The trail is now capped at the newest
``TRASH_RETAIN`` passes, which is still far more than anyone undoes. Runs at
startup and after every pass, so the directory never drifts above the cap.

The survivor set comes from the index, not from mtimes: a verdict's
``reviewed_at`` is the fact, the file's timestamp is a side-effect of it.
Anything in ``trash/`` the index does not vouch for -- orphans from before the
``reviewed_name`` column existed -- is deleted along with the old passes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from python_pkg.wsg_grabber import files, logs, paths, store_verdicts
from python_pkg.wsg_grabber.constants import TRASH_RETAIN

if TYPE_CHECKING:
    import sqlite3


def prune_trash(conn: sqlite3.Connection, retain: int = TRASH_RETAIN) -> int:
    """Delete every trashed file except the *retain* most recent passes.

    Files go first, rows second: a crash in between leaves rows that still say
    ``PASSED`` for files that are gone, which undo already copes with by
    forgetting the verdict. The reverse order would leave undoable-looking
    files the index had already written off.

    Args:
        conn: Open connection.
        retain: How many passes stay on disk and undoable.

    Returns:
        int: Files deleted.
    """
    trash = paths.trash_dir()
    survivors = store_verdicts.recent_passed_names(conn, retain)
    removed = 0
    if trash.is_dir():
        for entry in trash.iterdir():
            if entry.name in survivors or not entry.is_file():
                continue
            removed += files.remove(entry)
    purged = store_verdicts.purge_older_passes(conn, retain)
    if removed or purged:
        logs.event(
            "trash.pruned",
            removed=removed,
            purged_rows=purged,
            retained=len(survivors),
        )
    return removed
