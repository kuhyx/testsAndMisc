"""Tests for the trash cap."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from python_pkg.wsg_grabber import db, files, paths, store, store_verdicts
from python_pkg.wsg_grabber._prune import prune_trash
from python_pkg.wsg_grabber.models import RemoteFile
from python_pkg.wsg_grabber.states import FileState

if TYPE_CHECKING:
    from collections.abc import Iterator
    import sqlite3


@pytest.fixture
def conn() -> Iterator[sqlite3.Connection]:
    """Open a sandboxed index with the on-disk layout in place.

    Yields:
        sqlite3.Connection: Closed afterwards.
    """
    paths.ensure_dirs()
    opened = db.open_index(paths.db_path())
    try:
        yield opened
    finally:
        opened.close()


def _passed(conn: sqlite3.Connection, index: int, reviewed_at: str) -> str:
    """Record one pass whose file sits in trash/.

    Args:
        conn: Open connection.
        index: Distinguishes files within a test.
        reviewed_at: Verdict timestamp, so ordering is explicit.

    Returns:
        str: Name of the trashed file.
    """
    md5 = f"md5-{index:04d}"
    name = f"{index:04d}.webm"
    store.record_files(
        conn,
        [
            RemoteFile(
                md5=md5,
                tim=index,
                ext=".webm",
                orig_name=name,
                fsize=1,
                width=1,
                height=1,
                thread_no=1,
                post_no=index,
            ),
        ],
    )
    store.mark_downloaded(conn, md5, name)
    store_verdicts.record_verdict(conn, md5, FileState.PASSED, name)
    conn.execute("UPDATE files SET reviewed_at = ? WHERE md5 = ?", (reviewed_at, md5))
    (paths.trash_dir() / name).write_bytes(b"v")
    return name


def test_keeps_only_the_newest_passes(conn: sqlite3.Connection) -> None:
    names = [_passed(conn, i, f"2026-09-{i + 1:02d}") for i in range(5)]

    assert prune_trash(conn, retain=2) == 3

    assert sorted(p.name for p in paths.trash_dir().iterdir()) == names[3:]
    assert store.state_of(conn, "md5-0000") is FileState.PURGED
    assert store.state_of(conn, "md5-0004") is FileState.PASSED
    assert store_verdicts.reviewed_count(conn) == 2


def test_orphans_without_an_index_row_are_deleted_too(
    conn: sqlite3.Connection,
) -> None:
    _passed(conn, 1, "2026-09-01")
    (paths.trash_dir() / "orphan.webm").write_bytes(b"?")
    (paths.trash_dir() / "subdir").mkdir()

    assert prune_trash(conn, retain=5) == 1

    assert not (paths.trash_dir() / "orphan.webm").exists()
    assert (paths.trash_dir() / "0001.webm").exists()
    assert (paths.trash_dir() / "subdir").is_dir()


def test_under_the_cap_is_a_no_op(conn: sqlite3.Connection) -> None:
    _passed(conn, 1, "2026-09-01")
    assert prune_trash(conn, retain=5) == 0
    assert store.state_of(conn, "md5-0001") is FileState.PASSED


def test_missing_trash_dir_is_tolerated(conn: sqlite3.Connection) -> None:
    paths.trash_dir().rmdir()
    assert prune_trash(conn) == 0


def test_a_pass_whose_file_was_forgotten_is_purged(conn: sqlite3.Connection) -> None:
    """A row with no reviewed_name cannot be undone, so it is written off."""
    _passed(conn, 1, "2026-09-01")
    store_verdicts.forget_verdict(conn, "md5-0001")

    prune_trash(conn, retain=5)

    assert store.state_of(conn, "md5-0001") is FileState.PURGED


def test_purged_rows_are_still_known_to_the_catalog(conn: sqlite3.Connection) -> None:
    _passed(conn, 1, "2026-09-01")
    prune_trash(conn, retain=0)
    assert "md5-0001" in store.known_md5s(conn)


def test_remove_reports_whether_anything_was_there() -> None:
    target = paths.data_dir() / "x"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"")
    assert files.remove(target) is True
    assert files.remove(target) is False
