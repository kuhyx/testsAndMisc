"""The background worker: walk the board, fetch files, announce each one.

Structured so that :meth:`Worker.run_once` performs exactly one unit of work
and returns. The threaded loop is a thin wrapper around it, which is what lets
the tests drive the whole state machine synchronously without starting a thread
-- important because pytest treats warnings as errors and a leaked thread would
fail the suite.

The worker never touches Tk. It publishes events onto a queue that the UI
drains from its own event loop.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
import sqlite3
import threading
import time
from typing import TYPE_CHECKING

import requests

from python_pkg.wsg_grabber import net, scanner, store
from python_pkg.wsg_grabber._fetch import DownloadMixin
from python_pkg.wsg_grabber._scan import ScanMixin
from python_pkg.wsg_grabber.constants import (
    IDLE_POLL_S,
    IDLE_RESCAN_S,
)
from python_pkg.wsg_grabber.models import (
    JsonResponse,
    ScanFinished,
    TaskKind,
    ThreadRef,
    WorkerFailed,
)

_LOGGER = logging.getLogger(__name__)

# Every failure family this worker can plausibly hit: the network, the disk,
# the index, and bad data coming back from the board. Named explicitly rather
# than catching Exception, which the linters reject and which would also
# swallow genuine programming errors that ought to be loud.
_RECOVERABLE = (
    ArithmeticError,
    OSError,
    RuntimeError,
    ValueError,
    LookupError,
    TypeError,
    AttributeError,
    sqlite3.Error,
    requests.RequestException,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path
    import queue

    from python_pkg.wsg_grabber.models import DownloadEvent


@dataclass
class WorkerDeps:
    """Collaborators supplied to the worker, so tests can swap them out."""

    conn: sqlite3.Connection
    session: requests.Session
    incoming: Path
    events: queue.SimpleQueue[DownloadEvent]
    stop: threading.Event = field(default_factory=threading.Event)
    include_archive: bool = True


class Worker(ScanMixin, DownloadMixin):
    """Walks /wsg/ and downloads every file it has not seen before.

    The board-walking and file-fetching halves live in _scan and _fetch to
    keep this module under the 250-line cap; they are mixins because the
    tests drive their methods as bound attributes of a Worker.
    """

    def __init__(self, deps: WorkerDeps) -> None:
        """Store collaborators and initialise scan bookkeeping.

        Args:
            deps: Connection, session, destination and event queue.
        """
        self._deps = deps
        self._pending_threads: list[ThreadRef] = []
        self._catalog_fresh = False
        self._downloaded = 0
        self._last_request = 0.0
        self._finished_announced = False
        self._sweep_finished_at = 0.0

    @property
    def downloaded(self) -> int:
        """Return how many files this worker has fetched.

        Returns:
            int: Completed downloads since construction.
        """
        return self._downloaded

    def run(self) -> None:
        """Loop until the stop flag is set, reporting any crash to the UI.

        Failures on a background thread would otherwise vanish, leaving the
        reviewer waiting for downloads that never arrive, so anything in
        ``_RECOVERABLE`` is logged and surfaced in the status bar. The session
        and connection are closed on every exit path. The suite does not police
        that for us: ``meta/pyproject.toml`` downgrades
        ``PytestUnraisableExceptionWarning``, so a leak here would pass CI
        unnoticed.
        """
        try:
            while not self._deps.stop.is_set():
                self.run_once()
        except _RECOVERABLE as exc:
            _LOGGER.exception("wsg download worker stopped")
            self._publish(WorkerFailed(message=str(exc)))
        finally:
            self._deps.session.close()
            self._deps.conn.close()

    def run_once(self) -> TaskKind:
        """Perform one unit of work and return what it was.

        Returns:
            TaskKind: The action taken, so a caller can drive the worker step
            by step.
        """
        task = scanner.choose_task(
            store.pending_downloads(self._deps.conn),
            len(self._pending_threads),
            catalog_fresh=self._catalog_fresh,
        )
        if task is TaskKind.DOWNLOAD:
            self._download_one()
        elif task is TaskKind.SCAN:
            self._scan_step()
        else:
            self._idle()
        return task

    def _idle(self) -> None:
        """Report the board exhausted, then poll again after a quiet period.

        The rescan is deliberately not immediate. Resetting the catalogue every
        idle tick would walk the board once a second and re-announce completion
        each time; waiting keeps a finished sweep quiet until there is a real
        chance of new content.
        """
        self._announce_finished()
        self._deps.stop.wait(IDLE_POLL_S)
        if time.monotonic() - self._sweep_finished_at >= IDLE_RESCAN_S:
            self._catalog_fresh = False
            self._finished_announced = False

    def _announce_finished(self) -> None:
        """Emit ScanFinished once per completed sweep of the board."""
        if self._finished_announced:
            return
        self._finished_announced = True
        self._sweep_finished_at = time.monotonic()
        self._publish(ScanFinished())

    def _get_json(self, url: str, stamp: str | None = None) -> JsonResponse:
        """Fetch JSON while respecting the one-request-per-second rule.

        Args:
            url: Absolute API URL.
            stamp: Stored ``Last-Modified`` to send conditionally.

        Returns:
            JsonResponse: The decoded response.
        """
        self._wait_for_slot()
        return net.get_json(self._deps.session, url, stamp)

    def _wait_for_slot(self) -> None:
        """Sleep just long enough to stay within the API's rate limit."""
        now = time.monotonic()
        delay = scanner.next_delay(self._last_request, now)
        if delay > 0:
            self._deps.stop.wait(delay)
        self._last_request = time.monotonic()

    def _publish(self, event: DownloadEvent) -> None:
        """Hand an event to the UI thread.

        Args:
            event: What happened.
        """
        self._deps.events.put(event)


def start(
    build_deps: Callable[[], WorkerDeps],
    on_failure: Callable[[str], None] = lambda _message: None,
) -> threading.Thread:
    """Run a worker on its own non-daemon thread.

    A *factory* rather than ready-made dependencies, because sqlite forbids
    using a connection from any thread but the one that opened it. Building
    them inside the thread keeps ownership and disposal on the same side of the
    boundary; passing a pre-opened connection in raises ProgrammingError the
    moment the worker closes it.

    Args:
        build_deps: Called on the new thread to open the connection, session
            and everything else the worker owns.
        on_failure: Called with a message when *build_deps* itself fails, so
            the UI learns there will be no downloads.

    Returns:
        threading.Thread: The started thread; set the stop flag, then join it.
    """

    def _run() -> None:
        try:
            deps = build_deps()
        except _RECOVERABLE as exc:
            # Worker.run reports its own failures, but a crash while building
            # the connection and session happens before there is a Worker at
            # all. Without this the reviewer waits on downloads forever and the
            # only trace is threading.excepthook.
            _LOGGER.exception("wsg worker could not start")
            on_failure(str(exc))
            return
        Worker(deps).run()

    thread = threading.Thread(target=_run, name="wsg-downloader", daemon=False)
    thread.start()
    return thread
