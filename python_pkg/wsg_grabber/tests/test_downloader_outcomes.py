"""Tests for how completed and failed downloads are recorded."""

from __future__ import annotations

import queue
import threading
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from python_pkg.wsg_grabber import db, downloader, net, store
from python_pkg.wsg_grabber.models import (
    Downloaded,
    DownloadEvent,
    DownloadResult,
    FileReady,
    JsonResponse,
    Outcome,
    RemoteFile,
    TaskKind,
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


def test_a_completed_download_is_renamed_and_announced(
    deps: downloader.WorkerDeps,
) -> None:
    worker = downloader.Worker(deps)
    store.record_files(deps.conn, [_remote()])

    def fake_download(_session: object, transfer: net.Transfer) -> DownloadResult:
        transfer.part_path.write_bytes(_BODY)
        return DownloadResult(outcome=Outcome.COMPLETED, bytes_done=len(_BODY))

    with patch.object(net, "download", side_effect=fake_download):
        assert worker.run_once() is TaskKind.DOWNLOAD

    events = _drain(deps.events)
    ready = [event for event in events if isinstance(event, FileReady)]
    assert len(ready) == 1
    assert ready[0].item.md5 == _MD5
    assert ready[0].item.path.exists()
    assert not ready[0].item.path.name.endswith(".part")
    assert ready[0].item.orig_name == "clip.webm"
    assert any(isinstance(event, Downloaded) for event in events)
    assert worker.downloaded == 1
    assert store.counts(deps.conn)[FileState.READY.value] == 1


def test_a_404_is_terminal_and_never_retried(deps: downloader.WorkerDeps) -> None:
    """This is what stops a fallen-off thread being re-fetched every run."""
    worker = downloader.Worker(deps)
    store.record_files(deps.conn, [_remote()])
    with patch.object(
        net,
        "download",
        return_value=DownloadResult(outcome=Outcome.NOT_FOUND, bytes_done=0),
    ):
        worker.run_once()
    assert store.counts(deps.conn)[FileState.GONE.value] == 1
    assert store.pending_downloads(deps.conn) == 0
