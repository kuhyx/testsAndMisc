"""Tests for undoing verdicts in a review session."""

from __future__ import annotations

import queue
import threading
from typing import TYPE_CHECKING

import pytest

from python_pkg.wsg_grabber import (
    app,
    db,
    paths,
    store,
)
from python_pkg.wsg_grabber.models import RemoteFile, Verdict
from python_pkg.wsg_grabber.states import FileState

if TYPE_CHECKING:
    from collections.abc import Iterator

_MD5 = "Nz9OEKdMuMZEdYE6eLTKmA=="


@pytest.fixture
def session() -> Iterator[app.Session]:
    """Build a session over a sandboxed index, with no worker running.

    Yields:
        app.Session: Session whose connection is closed afterwards.
    """
    paths.ensure_dirs()
    conn = db.open_index(paths.db_path())
    built = app.Session(conn=conn, events=queue.SimpleQueue(), stop=threading.Event())
    try:
        yield built
    finally:
        conn.close()


def _downloaded(session: app.Session, name: str = "clip") -> None:
    """Put one downloaded, unreviewed file into the index and on disk.

    Args:
        session: The session to populate.
        name: Local filename stem.
    """
    store.record_files(
        session.conn,
        [
            RemoteFile(
                md5=_MD5,
                tim=1,
                ext=".webm",
                orig_name=name,
                fsize=5,
                width=4,
                height=3,
                thread_no=7,
                post_no=1,
            ),
        ],
    )
    local = f"{name}.webm"
    (paths.incoming_dir() / local).write_bytes(b"video")
    store.mark_downloaded(session.conn, _MD5, local)


def test_undo_puts_a_kept_file_back_in_the_queue(session: app.Session) -> None:
    """The misclick this exists for: kept something you meant to pass."""
    _downloaded(session)
    state = session.commit(app.initial_state(session), Verdict.KEEP)
    assert (paths.keep_dir() / "clip.webm").exists()

    state = session.undo(state)
    assert not (paths.keep_dir() / "clip.webm").exists()
    assert (paths.incoming_dir() / "clip.webm").exists()
    assert store.state_of(session.conn, _MD5) is FileState.READY
    assert state.kept == 0
    assert state.current is not None
    assert state.current.md5 == _MD5


def test_undo_puts_a_passed_file_back(session: app.Session) -> None:
    _downloaded(session)
    state = session.commit(app.initial_state(session), Verdict.SKIP)
    assert (paths.trash_dir() / "clip.webm").exists()

    state = session.undo(state)
    assert (paths.incoming_dir() / "clip.webm").exists()
    assert not (paths.trash_dir() / "clip.webm").exists()
    assert state.passed == 0


def test_undo_survives_a_collision_rename(session: app.Session) -> None:
    """A verdict may have renamed the file; undo must follow the real name."""
    _downloaded(session)
    (paths.trash_dir() / "clip.webm").write_bytes(b"older")
    state = session.commit(app.initial_state(session), Verdict.SKIP)
    assert (paths.trash_dir() / "clip-2.webm").exists()

    state = session.undo(state)
    assert (paths.incoming_dir() / "clip.webm").read_bytes() == b"video"
    assert (paths.trash_dir() / "clip.webm").read_bytes() == b"older"
    assert not (paths.trash_dir() / "clip-2.webm").exists()
