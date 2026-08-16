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
