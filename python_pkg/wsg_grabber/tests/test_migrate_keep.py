"""Tests for moving kept videos out of the data dir."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from python_pkg.wsg_grabber import db, paths, store, store_verdicts
from python_pkg.wsg_grabber._migrate_keep import migrate_keep
from python_pkg.wsg_grabber.models import RemoteFile
from python_pkg.wsg_grabber.states import FileState

if TYPE_CHECKING:
    from collections.abc import Iterator
    import sqlite3


@pytest.fixture
def conn() -> Iterator[sqlite3.Connection]:
    """Open a sandboxed index.

    Yields:
        sqlite3.Connection: Closed afterwards.
    """
    paths.ensure_dirs()
    opened = db.open_index(paths.db_path())
    try:
        yield opened
    finally:
        opened.close()


def _kept(conn: sqlite3.Connection, name: str, payload: bytes) -> None:
    """Record a keep whose file sits in the legacy keep/.

    Args:
        conn: Open connection.
        name: Filename.
        payload: File contents.
    """
    store.record_files(
        conn,
        [
            RemoteFile(
                md5=f"md5-{name}",
                tim=1,
                ext=".webm",
                orig_name=name,
                fsize=len(payload),
                width=1,
                height=1,
                thread_no=1,
                post_no=1,
            ),
        ],
    )
    store.mark_downloaded(conn, f"md5-{name}", name)
    store_verdicts.record_verdict(conn, f"md5-{name}", FileState.KEPT, name)
    paths.legacy_keep_dir().mkdir(parents=True, exist_ok=True)
    (paths.legacy_keep_dir() / name).write_bytes(payload)


def test_moves_everything_and_removes_the_empty_legacy_dir(
    conn: sqlite3.Connection,
) -> None:
    _kept(conn, "a.webm", b"aa")
    _kept(conn, "b.webm", b"bb")

    assert migrate_keep(conn) == 2

    assert (paths.keep_dir() / "a.webm").read_bytes() == b"aa"
    assert (paths.keep_dir() / "b.webm").read_bytes() == b"bb"
    assert not paths.legacy_keep_dir().exists()


def test_no_legacy_dir_is_a_no_op(conn: sqlite3.Connection) -> None:
    assert not paths.legacy_keep_dir().exists()
    assert migrate_keep(conn) == 0


def test_identical_copy_at_destination_drops_the_legacy_file(
    conn: sqlite3.Connection,
) -> None:
    _kept(conn, "a.webm", b"aa")
    paths.keep_dir().mkdir(parents=True, exist_ok=True)
    (paths.keep_dir() / "a.webm").write_bytes(b"zz")

    assert migrate_keep(conn) == 0

    assert (paths.keep_dir() / "a.webm").read_bytes() == b"zz"
    assert not paths.legacy_keep_dir().exists()


def test_name_clash_with_different_size_is_suffixed_and_reindexed(
    conn: sqlite3.Connection,
) -> None:
    _kept(conn, "a.webm", b"aa")
    paths.keep_dir().mkdir(parents=True, exist_ok=True)
    (paths.keep_dir() / "a.webm").write_bytes(b"other")

    assert migrate_keep(conn) == 1

    assert (paths.keep_dir() / "a.webm").read_bytes() == b"other"
    assert (paths.keep_dir() / "a-2.webm").read_bytes() == b"aa"
    row = conn.execute(
        "SELECT reviewed_name FROM files WHERE md5 = ?",
        ("md5-a.webm",),
    ).fetchone()
    assert row["reviewed_name"] == "a-2.webm"


def test_subdirectories_are_left_alone(conn: sqlite3.Connection) -> None:
    paths.legacy_keep_dir().mkdir(parents=True)
    (paths.legacy_keep_dir() / "nested").mkdir()

    assert migrate_keep(conn) == 0
    assert (paths.legacy_keep_dir() / "nested").is_dir()


def test_a_file_that_vanishes_mid_move_is_skipped(
    conn: sqlite3.Connection,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _kept(conn, "a.webm", b"aa")
    monkeypatch.setattr(
        "python_pkg.wsg_grabber._migrate_keep.files.apply_move",
        lambda _move: False,
    )
    assert migrate_keep(conn) == 0
