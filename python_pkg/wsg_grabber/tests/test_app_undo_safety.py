"""Tests that undo never clobbers an existing file."""

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
