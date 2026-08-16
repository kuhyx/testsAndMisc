"""Tests for retrying and resuming interrupted downloads."""

from __future__ import annotations

import queue
import threading
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from python_pkg.wsg_grabber import db, downloader, net, store
from python_pkg.wsg_grabber.models import (
    DownloadEvent,
    DownloadResult,
    JsonResponse,
    Outcome,
    RemoteFile,
)
from python_pkg.wsg_grabber.states import FileState

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

_MD5 = "Nz9OEKdMuMZEdYE6eLTKmA=="
_BODY = b"video bytes"


@pytest.fixture
def deps(tmp_path: Path) -> Iterator[downloader.WorkerDeps]:
    """Build worker dependencies backed by a sandboxed index.

    Args:
        tmp_path: Per-test temporary directory.

    Yields:
        downloader.WorkerDeps: Ready dependencies; resources closed after.
    """
    incoming = tmp_path / "incoming"
    incoming.mkdir()
    conn = db.open_index(tmp_path / "index.db")
    session = MagicMock()
    built = downloader.WorkerDeps(
        conn=conn,
        session=session,
        incoming=incoming,
        events=queue.SimpleQueue(),
        stop=threading.Event(),
        include_archive=False,
    )
    try:
        yield built
    finally:
        conn.close()


def _json(
    payload: object,
    *,
    last_modified: str | None = None,
    not_modified: bool = False,
    not_found: bool = False,
) -> JsonResponse:
    """Build a JsonResponse with sensible defaults.

    Args:
        payload: Decoded body.
        last_modified: Header value the response carried.
        not_modified: Whether the server answered 304.
        not_found: Whether the thread has gone.

    Returns:
        JsonResponse: Response double.
    """
    return JsonResponse(
        payload=payload,
        last_modified=last_modified,
        not_modified=not_modified,
        not_found=not_found,
    )


def _remote(md5: str = _MD5, tim: int = 1) -> RemoteFile:
    """Build a RemoteFile.

    Args:
        md5: Identity.
        tim: CDN stem.

    Returns:
        RemoteFile: Fixture value.
    """
    return RemoteFile(
        md5=md5,
        tim=tim,
        ext=".webm",
        orig_name="clip",
        fsize=len(_BODY),
        width=480,
        height=360,
        thread_no=7,
        post_no=tim,
    )


def _drain(events: queue.SimpleQueue[DownloadEvent]) -> list[DownloadEvent]:
    """Pull everything currently queued.

    Args:
        events: Queue to empty.

    Returns:
        list[DownloadEvent]: Events in order.
    """
    out: list[DownloadEvent] = []
    while not events.empty():
        out.append(events.get_nowait())
    return out


def test_a_transient_failure_is_retried(deps: downloader.WorkerDeps) -> None:
    worker = downloader.Worker(deps)
    store.record_files(deps.conn, [_remote()])
    with patch.object(
        net,
        "download",
        return_value=DownloadResult(outcome=Outcome.TRANSIENT, bytes_done=0),
    ):
        worker.run_once()
    assert store.counts(deps.conn)[FileState.FAILED.value] == 1
    assert store.pending_downloads(deps.conn) == 1


def test_a_transient_failure_gives_up_after_the_attempt_budget(
    deps: downloader.WorkerDeps,
) -> None:
    worker = downloader.Worker(deps)
    store.record_files(deps.conn, [_remote()])
    with patch.object(
        net,
        "download",
        return_value=DownloadResult(outcome=Outcome.TRANSIENT, bytes_done=0),
    ):
        for _ in range(3):
            worker.run_once()
    assert store.counts(deps.conn)[FileState.GONE.value] == 1


def test_a_retry_after_pauses_the_worker(deps: downloader.WorkerDeps) -> None:
    worker = downloader.Worker(deps)
    store.record_files(deps.conn, [_remote()])
    with (
        patch.object(
            net,
            "download",
            return_value=DownloadResult(
                outcome=Outcome.TRANSIENT,
                bytes_done=0,
                retry_after=5.0,
            ),
        ),
        patch.object(deps.stop, "wait") as waited,
    ):
        worker.run_once()
    assert any(call.args and call.args[0] == 5.0 for call in waited.call_args_list)


def test_a_checksum_mismatch_marks_the_file_corrupt(
    deps: downloader.WorkerDeps,
) -> None:
    worker = downloader.Worker(deps)
    store.record_files(deps.conn, [_remote()])
    with patch.object(
        net,
        "download",
        return_value=DownloadResult(outcome=Outcome.CHECKSUM_MISMATCH, bytes_done=0),
    ):
        worker.run_once()
    assert store.counts(deps.conn)[FileState.CORRUPT.value] == 1


def test_an_aborted_download_stays_resumable(deps: downloader.WorkerDeps) -> None:
    worker = downloader.Worker(deps)
    store.record_files(deps.conn, [_remote()])
    with patch.object(
        net,
        "download",
        return_value=DownloadResult(outcome=Outcome.ABORTED, bytes_done=4),
    ):
        worker.run_once()
    assert store.counts(deps.conn)[FileState.FAILED.value] == 1
    assert store.pending_downloads(deps.conn) == 1
