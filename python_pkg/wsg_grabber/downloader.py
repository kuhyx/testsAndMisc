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

from python_pkg.wsg_grabber import catalog, net, scanner, store, store_threads
from python_pkg.wsg_grabber.constants import (
    API_HOST,
    ARCHIVE_URL,
    BOARD,
    IDLE_POLL_S,
    IDLE_RESCAN_S,
    THREADS_URL,
)
from python_pkg.wsg_grabber.models import (
    Downloaded,
    FileReady,
    Indexed,
    JsonResponse,
    Outcome,
    ScanFinished,
    TaskKind,
    ThreadRef,
    WorkerFailed,
)
from python_pkg.wsg_grabber.states import (
    CLAIMABLE,
    FileEvent,
    FileState,
    next_state,
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

    from python_pkg.wsg_grabber.models import DownloadEvent, RemoteFile


@dataclass
class WorkerDeps:
    """Collaborators supplied to the worker, so tests can swap them out."""

    conn: sqlite3.Connection
    session: requests.Session
    incoming: Path
    events: queue.SimpleQueue[DownloadEvent]
    stop: threading.Event = field(default_factory=threading.Event)
    include_archive: bool = True


class Worker:
    """Walks /wsg/ and downloads every file it has not seen before."""

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

    def _scan_step(self) -> None:
        """Read the thread list, or fetch the next thread that changed."""
        if not self._catalog_fresh:
            self._refresh_thread_list()
            return
        ref = self._pending_threads.pop(0)
        self._fetch_thread(ref)

    def _refresh_thread_list(self) -> None:
        """Fetch ``threads.json`` and work out which threads to visit."""
        response = self._conditional_get(THREADS_URL)
        live = catalog.parse_thread_list(response.payload)
        if self._deps.include_archive:
            live = live + self._archive_refs()
        known = store_threads.known_threads(self._deps.conn)
        self._pending_threads = scanner.stale_threads(known, live)
        self._catalog_fresh = True
        self._finished_announced = False

    def _archive_refs(self) -> list[ThreadRef]:
        """Fetch the archive listing, tolerating boards without one.

        Returns:
            list[ThreadRef]: Archived threads, empty when unavailable.
        """
        response = self._conditional_get(ARCHIVE_URL)
        if response.not_found:
            return []
        return catalog.parse_archive(response.payload)

    def _conditional_get(self, url: str) -> JsonResponse:
        """Fetch a board-level endpoint, sending back the stamp we hold.

        Without this an idle reviewer re-fetches threads.json and archive.json
        unconditionally every cycle. With it an unchanged board costs a 304.

        Args:
            url: Absolute API URL.

        Returns:
            JsonResponse: The response; on 304 the payload is None and the
            caller keeps whatever it already knew.
        """
        stamp = store_threads.cached_last_modified(self._deps.conn, url)
        response = self._get_json(url, stamp)
        if not response.not_modified:
            store_threads.record_last_modified(
                self._deps.conn,
                url,
                response.last_modified,
            )
        return response

    def _fetch_thread(self, ref: ThreadRef) -> None:
        """Read one thread and record any files it introduces.

        Args:
            ref: Thread to fetch.
        """
        url = f"{API_HOST}/{BOARD}/thread/{ref.thread_no}.json"
        stamp = store_threads.http_last_modified(self._deps.conn, ref.thread_no)
        response = self._get_json(url, stamp)
        if response.not_found:
            store_threads.mark_thread_gone(self._deps.conn, ref.thread_no)
            return
        if response.not_modified:
            store_threads.record_thread(self._deps.conn, ref, stamp)
            return

        parsed = catalog.parse_thread(ref.thread_no, response.payload)
        known = store.known_md5s(self._deps.conn)
        added = store.record_files(
            self._deps.conn,
            catalog.new_files(parsed, known),
        )
        self._write_off_deleted(catalog.deleted_md5s(response.payload), known)
        store_threads.record_thread(self._deps.conn, ref, response.last_modified)
        if added:
            self._publish(Indexed(known=len(known) + added))

    def _write_off_deleted(self, gone: set[str], known: set[str]) -> None:
        """Mark not-yet-fetched files terminal when the board drops them.

        Only files still waiting to download are affected. Once the bytes are
        on disk the post being deleted upstream is irrelevant, so an already
        downloaded or reviewed file keeps its state -- the same rule the
        transition table encodes by rejecting ``READY + DELETED_UPSTREAM``.

        Args:
            gone: md5s the board reports as deleted.
            known: md5s already in the index.
        """
        for digest in gone & known:
            if store.state_of(self._deps.conn, digest) not in CLAIMABLE:
                continue
            store.set_state(
                self._deps.conn,
                digest,
                FileState.GONE,
                error="deleted upstream",
            )

    def _download_one(self) -> None:
        """Claim the next pending file and fetch it."""
        claimed = store.claim_next(self._deps.conn)
        if claimed is None:
            return
        part = (
            self._deps.incoming
            / f"{store.local_name(claimed.md5, claimed.tim, claimed.ext)}.part"
        )
        self._wait_for_slot()
        result = net.download(
            self._deps.session,
            net.Transfer(
                url=catalog.media_url(claimed.tim, claimed.ext),
                part_path=part,
                expected_md5=claimed.md5,
                expected_size=claimed.fsize,
                should_stop=self._deps.stop.is_set,
                on_progress=lambda done: store.record_progress(
                    self._deps.conn,
                    claimed.md5,
                    done,
                ),
            ),
        )
        self._apply_result(claimed, part, result.outcome, result.retry_after)

    def _apply_result(
        self,
        claimed: RemoteFile,
        part: Path,
        outcome: Outcome,
        retry_after: float | None,
    ) -> None:
        """Translate a download outcome into index state and an event.

        Args:
            claimed: The file that was attempted.
            part: Its partial-file path.
            outcome: How the download ended.
            retry_after: Server-requested pause, when supplied.
        """
        if outcome is Outcome.ABORTED:
            store.set_state(self._deps.conn, claimed.md5, FileState.FAILED)
            return
        if outcome is Outcome.COMPLETED:
            final = part.with_suffix("")
            part.replace(final)
            store.mark_downloaded(self._deps.conn, claimed.md5, final.name)
            self._downloaded += 1
            self._publish(
                FileReady(
                    item=store.ready_item(claimed, final),
                ),
            )
            self._publish(Downloaded(count=self._downloaded))
            return

        event = {
            Outcome.NOT_FOUND: FileEvent.NOT_FOUND,
            Outcome.CHECKSUM_MISMATCH: FileEvent.CHECKSUM_MISMATCH,
            Outcome.TRANSIENT: FileEvent.TRANSIENT_ERROR,
        }[outcome]
        attempts = store.attempts_for(self._deps.conn, claimed.md5)
        store.set_state(
            self._deps.conn,
            claimed.md5,
            next_state(FileState.DOWNLOADING, event, attempts),
            error=outcome.value,
        )
        if retry_after is not None:
            self._deps.stop.wait(scanner.backoff_seconds(attempts, retry_after))

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
