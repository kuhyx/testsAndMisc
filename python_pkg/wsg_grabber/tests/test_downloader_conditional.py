"""Tests for conditional board fetches and stored stamps."""

from __future__ import annotations

import queue
import threading
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from python_pkg.wsg_grabber import db, downloader, net, store_threads
from python_pkg.wsg_grabber.constants import THREADS_URL
from python_pkg.wsg_grabber.models import (
    DownloadEvent,
    JsonResponse,
    RemoteFile,
)

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


def test_the_board_endpoints_are_fetched_conditionally(
    deps: downloader.WorkerDeps,
) -> None:
    """Without this an idle reviewer re-fetches the board unconditionally forever."""
    deps.include_archive = True
    worker = downloader.Worker(deps)
    stamp = "Mon, 27 Jul 2026 10:00:00 GMT"
    with patch.object(
        net,
        "get_json",
        return_value=_json([], last_modified=stamp),
    ) as fake:
        worker.run_once()
        sent_first = [call.args[2] for call in fake.call_args_list]
        worker._catalog_fresh = False
        fake.reset_mock()
        worker.run_once()
        sent_again = [call.args[2] for call in fake.call_args_list]

    assert sent_first == [None, None]  # nothing stored yet
    assert sent_again == [stamp, stamp]  # the stamp goes back


def test_a_304_on_the_board_keeps_the_stored_stamp(
    deps: downloader.WorkerDeps,
) -> None:
    worker = downloader.Worker(deps)
    stamp = "Mon, 27 Jul 2026 10:00:00 GMT"
    with patch.object(net, "get_json", return_value=_json([], last_modified=stamp)):
        worker.run_once()
    with patch.object(net, "get_json", return_value=_json(None, not_modified=True)):
        worker._catalog_fresh = False
        worker.run_once()
    assert store_threads.cached_last_modified(deps.conn, THREADS_URL) == stamp


def test_a_worker_that_cannot_build_its_resources_reports_it(
    tmp_path: Path,
) -> None:
    """Otherwise the reviewer waits on downloads that will never come."""
    reported: list[str] = []
    thread = downloader.start(
        lambda: (_ for _ in ()).throw(OSError("no database")),
        reported.append,
    )
    thread.join(timeout=5)
    assert not thread.is_alive()
    assert reported
    assert "no database" in reported[0]
