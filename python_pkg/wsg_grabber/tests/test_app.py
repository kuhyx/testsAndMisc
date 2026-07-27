"""Tests for the composition root and verdict application."""

from __future__ import annotations

import queue
import threading
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from python_pkg.wsg_grabber import (
    app,
    db,
    downloader,
    paths,
    review,
    store,
    store_verdicts,
)
from python_pkg.wsg_grabber.models import RemoteFile, Verdict
from python_pkg.wsg_grabber.states import FileState

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

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


def test_keep_moves_the_file_and_records_it(session: app.Session) -> None:
    _downloaded(session)
    state = app.initial_state(session)
    result = session.commit(state, Verdict.KEEP)

    assert (paths.keep_dir() / "clip.webm").exists()
    assert not (paths.incoming_dir() / "clip.webm").exists()
    assert store.state_of(session.conn, _MD5) is FileState.KEPT
    assert result.kept == 1


def test_pass_moves_to_trash_and_never_deletes(session: app.Session) -> None:
    """The whole point of trash/: a pass is reversible until the user says so."""
    _downloaded(session)
    state = app.initial_state(session)
    result = session.commit(state, Verdict.SKIP)

    assert (paths.trash_dir() / "clip.webm").exists()
    assert (paths.trash_dir() / "clip.webm").read_bytes() == b"video"
    assert store.state_of(session.conn, _MD5) is FileState.PASSED
    assert result.passed == 1


def test_a_name_collision_in_the_destination_is_resolved(
    session: app.Session,
) -> None:
    _downloaded(session)
    (paths.keep_dir() / "clip.webm").write_bytes(b"older")
    session.commit(app.initial_state(session), Verdict.KEEP)

    assert (paths.keep_dir() / "clip.webm").read_bytes() == b"older"
    assert (paths.keep_dir() / "clip-2.webm").read_bytes() == b"video"


def test_a_verdict_on_a_vanished_file_writes_it_off(session: app.Session) -> None:
    _downloaded(session)
    state = app.initial_state(session)
    (paths.incoming_dir() / "clip.webm").unlink()

    result = session.commit(state, Verdict.KEEP)
    assert store.state_of(session.conn, _MD5) is FileState.GONE
    assert result.kept == 0
    assert result.current is None


def test_a_verdict_with_nothing_showing_is_ignored(session: app.Session) -> None:
    state = review.initial_state(0, [])
    assert session.commit(state, Verdict.KEEP) is state
    assert session.missing(state) is state


def test_initial_state_resumes_a_previous_run(session: app.Session) -> None:
    _downloaded(session)
    state = app.initial_state(session)
    assert state.current is not None
    assert state.current.md5 == _MD5
    assert state.indexed == 1


def test_shutdown_stops_the_worker_and_closes_the_index() -> None:
    paths.ensure_dirs()
    conn = db.open_index(paths.db_path())
    worker = MagicMock()
    worker.is_alive.return_value = False
    built = app.Session(
        conn=conn,
        events=queue.SimpleQueue(),
        stop=threading.Event(),
        worker=worker,
    )
    built.shutdown()
    assert built.stop.is_set()
    worker.join.assert_called_once()
    assert built.worker is None


def test_shutdown_without_a_worker() -> None:
    paths.ensure_dirs()
    conn = db.open_index(paths.db_path())
    built = app.Session(conn=conn, events=queue.SimpleQueue(), stop=threading.Event())
    built.shutdown()
    assert built.stop.is_set()


def test_open_session_starts_a_worker_owning_its_own_connection() -> None:
    """sqlite forbids sharing a connection across threads, so the factory must
    build one on the worker's side of the boundary."""
    captured: list[downloader.WorkerDeps] = []

    def fake_start(
        build: Callable[[], downloader.WorkerDeps],
        _on_failure: Callable[[str], None] = lambda _m: None,
    ) -> MagicMock:
        deps = build()
        captured.append(deps)
        deps.conn.close()
        deps.session.close()
        return MagicMock()

    with patch.object(downloader, "start", side_effect=fake_start):
        built = app.open_session(include_archive=False)
    try:
        assert captured
        assert captured[0].incoming == paths.incoming_dir()
        assert not captured[0].include_archive
        assert paths.incoming_dir().is_dir()
        assert paths.trash_dir().is_dir()
    finally:
        built.shutdown()


def test_open_session_recovers_interrupted_downloads() -> None:
    paths.ensure_dirs()
    conn = db.open_index(paths.db_path())
    store.record_files(
        conn,
        [
            RemoteFile(
                md5=_MD5,
                tim=1,
                ext=".webm",
                orig_name="x",
                fsize=1,
                width=1,
                height=1,
                thread_no=1,
                post_no=1,
            ),
        ],
    )
    store.claim_next(conn)
    conn.close()

    with patch.object(downloader, "start", return_value=MagicMock()):
        built = app.open_session()
    try:
        assert store.pending_downloads(built.conn) == 1
    finally:
        built.shutdown()


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


def test_undo_never_overwrites_a_file_sitting_in_incoming(
    session: app.Session,
) -> None:
    """A verdict must never be reversed on top of another video.

    Path.replace clobbers silently, so undo picks a collision-free name the
    same way commit does.
    """
    _downloaded(session)
    state = session.commit(app.initial_state(session), Verdict.KEEP)
    # something else now occupies the name the file used to have
    (paths.incoming_dir() / "clip.webm").write_bytes(b"DO NOT DESTROY ME")

    session.undo(state)

    assert (paths.incoming_dir() / "clip.webm").read_bytes() == b"DO NOT DESTROY ME"
    assert (paths.incoming_dir() / "clip-2.webm").read_bytes() == b"video"
    row = session.conn.execute(
        "SELECT local_name FROM files WHERE md5 = ?",
        (_MD5,),
    ).fetchone()
    assert row["local_name"] == "clip-2.webm"


def test_a_missing_file_never_clobbers_an_existing_verdict(
    session: app.Session,
) -> None:
    """Two reviewers on one index must not corrupt each other's undo trail."""
    _downloaded(session)
    state = app.initial_state(session)
    session.commit(state, Verdict.KEEP)
    assert store_verdicts.reviewed_count(session.conn) == 1

    # the same item, still queued in a second reviewer, whose file is now gone
    session.missing(state)

    assert store.state_of(session.conn, _MD5) is FileState.KEPT
    assert store_verdicts.reviewed_count(session.conn) == 1


def test_open_session_closes_the_index_if_the_worker_cannot_start() -> None:
    with (
        patch.object(downloader, "start", side_effect=RuntimeError("no thread")),
        pytest.raises(RuntimeError),
    ):
        app.open_session()
    # a second open must succeed, which it cannot if the first leaked a handle
    with patch.object(downloader, "start", return_value=MagicMock()):
        again = app.open_session()
    again.shutdown()


def test_a_worker_that_outlives_the_join_is_not_silently_forgotten(
    session: app.Session,
) -> None:
    worker = MagicMock()
    worker.is_alive.return_value = True
    session.worker = worker
    session.shutdown()
    assert session.worker is worker  # handle kept so the failure is visible
