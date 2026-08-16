"""Fetching one claimed file and recording how it went.

Split out of :mod:`python_pkg.wsg_grabber.downloader` to keep it under the
250-line cap. A mixin rather than free functions because the tests drive
``worker._download_one()`` as a bound method and it shares the worker's
download tally.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from python_pkg.wsg_grabber import catalog, net, scanner, store
from python_pkg.wsg_grabber._worker_base import WorkerBase
from python_pkg.wsg_grabber.models import Downloaded, FileReady, Outcome
from python_pkg.wsg_grabber.states import FileEvent, FileState, next_state

if TYPE_CHECKING:
    from pathlib import Path

    from python_pkg.wsg_grabber.models import RemoteFile


class DownloadMixin(WorkerBase):
    """The file-fetching half of :class:`~.downloader.Worker`."""

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
