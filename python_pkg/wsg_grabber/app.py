"""Wires the pieces together and owns an orderly shutdown.

Kept separate from :mod:`python_pkg.wsg_grabber.cli` so the composition can be
exercised without argument parsing, and separate from
:mod:`python_pkg.wsg_grabber.ui` so nothing here needs a display.
"""

from __future__ import annotations

from dataclasses import dataclass
import queue
import threading
from typing import TYPE_CHECKING

from python_pkg.wsg_grabber import (
    db,
    downloader,
    files,
    logs,
    net,
    paths,
    review,
    store,
    store_verdicts,
    verdict,
)
from python_pkg.wsg_grabber.constants import JOIN_TIMEOUT_S
from python_pkg.wsg_grabber.models import FileMove, Verdict, WorkerFailed
from python_pkg.wsg_grabber.states import TERMINAL, FileState

if TYPE_CHECKING:
    import sqlite3

    from python_pkg.wsg_grabber.models import DownloadEvent
    from python_pkg.wsg_grabber.review import SessionState


@dataclass
class Session:
    """A running review session and everything it must clean up."""

    conn: sqlite3.Connection
    events: queue.SimpleQueue[DownloadEvent]
    stop: threading.Event
    worker: threading.Thread | None = None

    def commit(self, state: SessionState, choice: Verdict) -> SessionState:
        """Apply a verdict: move the file, record it, advance the queue.

        Args:
            state: Current session state.
            choice: What the user decided.

        Returns:
            SessionState: Updated state.
        """
        item = state.current
        if item is None:
            return state
        move = verdict.plan_move(
            item,
            choice,
            paths.keep_dir(),
            paths.trash_dir(),
            files.existing_names(
                verdict.target_dir(choice, paths.keep_dir(), paths.trash_dir()),
            ),
        )
        if not files.apply_move(move):
            logs.warning(
                "verdict.source_gone",
                file=move.src.name,
                choice=choice.value,
            )
            return self.missing(state)
        logs.event(
            "verdict.moved",
            choice=choice.value,
            src=str(move.src),
            dst=str(move.dst),
            md5=item.md5,
        )
        store_verdicts.record_verdict(
            self.conn,
            item.md5,
            verdict.target_state(choice),
            move.dst.name,
        )
        return review.on_verdict(state, choice)

    def undo(self, state: SessionState) -> SessionState:
        """Take back the last verdict, putting the file back in the queue.

        Args:
            state: Current session state.

        Returns:
            SessionState: Updated state showing the restored video.
        """
        action = store_verdicts.newest_verdict(self.conn, paths.incoming_dir())
        if action is None:
            return state
        source = (
            paths.keep_dir() if action.choice is Verdict.KEEP else paths.trash_dir()
        ) / action.reviewed_name
        # Mirror what commit does: never assume the old name is free again.
        destination = verdict.unique_destination(
            paths.incoming_dir(),
            action.item.path.name,
            files.existing_names(paths.incoming_dir()),
        )
        back = FileMove(md5=action.item.md5, src=source, dst=destination)
        if not files.apply_move(back):
            # The file is no longer where the verdict left it -- most likely the
            # user cleared trash/ by hand. Drop it from the undo trail so a
            # second attempt does not keep failing on the same entry.
            logs.warning(
                "undo.file_gone",
                expected=str(source),
                md5=action.item.md5,
            )
            store_verdicts.forget_verdict(self.conn, action.item.md5)
            return review.forget_last(state)
        store_verdicts.restore_for_review(
            self.conn,
            action.item.md5,
            destination.name,
        )
        logs.event(
            "undo.applied",
            choice=action.choice.value,
            file=destination.name,
            restored_from=str(source),
            remaining=store_verdicts.reviewed_count(self.conn),
        )
        return review.on_undo(state, action)

    def missing(self, state: SessionState) -> SessionState:
        """Write off a video whose file has disappeared.

        Args:
            state: Current session state.

        Returns:
            SessionState: Updated state showing the next video.
        """
        item = state.current
        if item is None:
            return state
        # A row that already carries a verdict must not be forced to GONE: that
        # would drop it out of the undo trail while the in-memory count still
        # believes it is there, and the verdict itself would be unrecoverable.
        # Reachable when the same item is queued twice, e.g. two reviewers
        # running against one index.
        if store.state_of(self.conn, item.md5) in TERMINAL:
            logs.warning("missing.already_reviewed", md5=item.md5)
            return review.on_missing_locally(state)
        store.set_state(
            self.conn,
            item.md5,
            FileState.GONE,
            error="file missing locally",
        )
        return review.on_missing_locally(state)

    def shutdown(self) -> None:
        """Stop the worker and close the index.

        Joining matters: the worker owns a database connection and an HTTP
        session, and abandoning it leaks both. Note the suite does NOT catch
        that for us -- ``meta/pyproject.toml`` downgrades
        ``PytestUnraisableExceptionWarning`` to a warning -- so this has to be
        right by construction rather than by test pressure.
        """
        self.stop.set()
        if self.worker is not None:
            self.worker.join(timeout=JOIN_TIMEOUT_S)
            if self.worker.is_alive():
                # A worker blocked in a socket read can outlive the join, since
                # READ_TIMEOUT_S exceeds JOIN_TIMEOUT_S. Keep the handle so the
                # failure is visible rather than silently discarded.
                logs.warning("shutdown.worker_still_running")
            else:
                self.worker = None
        self.conn.close()


def open_session(*, include_archive: bool = True) -> Session:
    """Prepare storage and start the background worker.

    Args:
        include_archive: Whether to walk the board's archive as well.

    Returns:
        Session: A running session; call :meth:`Session.shutdown` when done.
    """
    paths.ensure_dirs()
    conn = db.open_index(paths.db_path())
    store.reset_in_flight(conn)
    events: queue.SimpleQueue[DownloadEvent] = queue.SimpleQueue()
    stop = threading.Event()
    session = Session(conn=conn, events=events, stop=stop)

    incoming = paths.incoming_dir()
    db_file = paths.db_path()

    def build() -> downloader.WorkerDeps:
        """Open the worker's own resources on the worker's own thread.

        Returns:
            downloader.WorkerDeps: Dependencies owned by the worker.
        """
        return downloader.WorkerDeps(
            conn=db.open_index(db_file),
            session=net.build_session(),
            incoming=incoming,
            events=events,
            stop=stop,
            include_archive=include_archive,
        )

    try:
        session.worker = downloader.start(
            build,
            lambda message: events.put(WorkerFailed(message=message)),
        )
    except BaseException:
        conn.close()
        raise
    return session


def initial_state(session: Session) -> SessionState:
    """Build the state a window should open with.

    Args:
        session: The running session.

    Returns:
        SessionState: Starting state, including anything left unreviewed by a
        previous run.
    """
    counts = store.counts(session.conn)
    return review.initial_state(
        counts.get("total", 0),
        store.ready_items(session.conn, paths.incoming_dir()),
        store_verdicts.reviewed_count(session.conn),
    )
