"""One-off move of kept videos out of the data dir.

Kept videos used to live in ``~/.local/share/wsg_grabber/keep``, which is
where nobody looks. They now go to the cloud folder (or ``~/Downloads``), and
this module carries the old directory's contents across on the first start
after the change. Idempotent: an empty or missing ``keep/`` is a no-op, and a
partial run just resumes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from python_pkg.wsg_grabber import files, logs, paths, store_verdicts, verdict
from python_pkg.wsg_grabber.models import FileMove

if TYPE_CHECKING:
    from pathlib import Path
    import sqlite3


def migrate_keep(conn: sqlite3.Connection) -> int:
    """Move everything in the legacy ``keep/`` into today's keep directory.

    A file already present at the destination with the same size is a
    duplicate of an earlier hand-copy and the legacy one is dropped. A name
    clash with a different size gets the usual ``-2`` suffix, and the index is
    told the new name so the verdict stays undoable.

    Args:
        conn: Open connection.

    Returns:
        int: Files moved.
    """
    legacy = paths.legacy_keep_dir()
    if not legacy.is_dir():
        return 0
    target = paths.keep_dir()
    target.mkdir(parents=True, exist_ok=True)
    taken = files.existing_names(target)
    moved = 0
    for entry in sorted(legacy.iterdir()):
        if not entry.is_file():
            continue
        if _is_duplicate(entry, target / entry.name):
            files.remove(entry)
            logs.event("keep.migrate_duplicate", file=entry.name)
            continue
        destination = verdict.unique_destination(target, entry.name, taken)
        if not files.apply_move(FileMove(md5="", src=entry, dst=destination)):
            continue
        taken.add(destination.name)
        moved += 1
        if destination.name != entry.name:
            store_verdicts.rename_kept(conn, entry.name, destination.name)
    if not any(legacy.iterdir()):
        legacy.rmdir()
    if moved:
        logs.event("keep.migrated", moved=moved, to=str(target))
    return moved


def _is_duplicate(source: Path, candidate: Path) -> bool:
    """Report whether *candidate* is already a copy of *source*.

    Args:
        source: Legacy file.
        candidate: Same name at the destination.

    Returns:
        bool: True when both exist with the same size.
    """
    return candidate.is_file() and candidate.stat().st_size == source.stat().st_size
