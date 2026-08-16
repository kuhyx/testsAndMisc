"""Walking the board: the thread list, the archive, and each changed thread.

Split out of :mod:`python_pkg.wsg_grabber.downloader` to keep it under the
250-line cap. This is a mixin rather than a set of free functions because the
tests drive these as bound methods (``worker._fetch_thread(...)``), and because
they share the worker's scan bookkeeping.

The bare annotations below declare what ``Worker.__init__`` actually sets, so
mypy can see the attributes without the mixin duplicating any of that state.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from python_pkg.wsg_grabber import catalog, scanner, store, store_threads
from python_pkg.wsg_grabber._worker_base import WorkerBase
from python_pkg.wsg_grabber.constants import (
    API_HOST,
    ARCHIVE_URL,
    BOARD,
    THREADS_URL,
)
from python_pkg.wsg_grabber.models import Indexed, ThreadRef
from python_pkg.wsg_grabber.states import CLAIMABLE, FileState

if TYPE_CHECKING:
    from python_pkg.wsg_grabber.models import JsonResponse


class ScanMixin(WorkerBase):
    """The board-walking half of :class:`~.downloader.Worker`."""

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
