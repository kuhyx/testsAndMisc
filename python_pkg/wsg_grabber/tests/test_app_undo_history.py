"""Tests for stepping back through several verdicts."""

from __future__ import annotations

import queue
import threading
from typing import TYPE_CHECKING

import pytest

from python_pkg.wsg_grabber import (
    app,
    db,
    paths,
    review,
    store,
    store_verdicts,
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


def test_undo_steps_back_through_several_verdicts(session: app.Session) -> None:
    for index in range(3):
        store.record_files(
            session.conn,
            [
                RemoteFile(
                    md5=f"M{index}",
                    tim=index,
                    ext=".webm",
                    orig_name=f"v{index}",
                    fsize=5,
                    width=1,
                    height=1,
                    thread_no=1,
                    post_no=index,
                ),
            ],
        )
        (paths.incoming_dir() / f"v{index}.webm").write_bytes(b"video")
        store.mark_downloaded(session.conn, f"M{index}", f"v{index}.webm")

    state = app.initial_state(session)
    for _ in range(3):
        state = session.commit(state, Verdict.SKIP)
    assert state.passed == 3

    for expected in ("M2", "M1", "M0"):
        state = session.undo(state)
        assert state.current is not None
        assert state.current.md5 == expected
    assert state.passed == 0
    assert not review.can_undo(state)


def test_undo_with_nothing_to_undo_is_a_no_op(session: app.Session) -> None:
    state = app.initial_state(session)
    assert session.undo(state) is state


def test_undo_gives_up_gracefully_when_the_file_was_removed(
    session: app.Session,
) -> None:
    """You may have emptied trash/ by hand; undo must not wedge on it."""
    _downloaded(session)
    state = session.commit(app.initial_state(session), Verdict.SKIP)
    (paths.trash_dir() / "clip.webm").unlink()

    state = session.undo(state)
    assert not review.can_undo(state)
    assert store.state_of(session.conn, _MD5) is FileState.PASSED


def test_undo_survives_quitting_and_reopening(session: app.Session) -> None:
    """The whole point of persisting the trail: undo is not lost on exit."""
    _downloaded(session)
    session.commit(app.initial_state(session), Verdict.SKIP)
    assert (paths.trash_dir() / "clip.webm").exists()
    session.conn.close()

    # a brand new session, as if the reviewer had been restarted
    reopened = app.Session(
        conn=db.open_index(paths.db_path()),
        events=queue.SimpleQueue(),
        stop=threading.Event(),
    )
    try:
        fresh = app.initial_state(reopened)
        assert fresh.undoable == 1
        restored = reopened.undo(fresh)
        assert (paths.incoming_dir() / "clip.webm").exists()
        assert store.state_of(reopened.conn, _MD5) is FileState.READY
        assert restored.current is not None
        assert restored.current.md5 == _MD5
        assert restored.undoable == 0
    finally:
        reopened.conn.close()


def test_the_undo_trail_is_unbounded(session: app.Session) -> None:
    """Any number of last verdicts, not a fixed window."""
    total = 25
    for index in range(total):
        store.record_files(
            session.conn,
            [
                RemoteFile(
                    md5=f"U{index:02d}",
                    tim=index,
                    ext=".webm",
                    orig_name=f"u{index:02d}",
                    fsize=5,
                    width=1,
                    height=1,
                    thread_no=1,
                    post_no=index,
                ),
            ],
        )
        (paths.incoming_dir() / f"u{index:02d}.webm").write_bytes(b"video")
        store.mark_downloaded(session.conn, f"U{index:02d}", f"u{index:02d}.webm")

    state = app.initial_state(session)
    for _ in range(total):
        state = session.commit(state, Verdict.SKIP)
    assert state.passed == total
    assert store_verdicts.reviewed_count(session.conn) == total

    for index in reversed(range(total)):
        state = session.undo(state)
        assert state.current is not None
        assert state.current.md5 == f"U{index:02d}"
    assert state.passed == 0
    assert store_verdicts.reviewed_count(session.conn) == 0
    assert len(list(paths.trash_dir().iterdir())) == 0
