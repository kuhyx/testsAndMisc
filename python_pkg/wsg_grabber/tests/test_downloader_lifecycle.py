"""Tests for worker idle announcements and shutdown."""

from __future__ import annotations

import queue
import threading
import time
from typing import TYPE_CHECKING, cast
from unittest.mock import MagicMock, patch

import pytest

from python_pkg.wsg_grabber import db, downloader, net
from python_pkg.wsg_grabber.constants import IDLE_RESCAN_S
from python_pkg.wsg_grabber.models import (
    DownloadEvent,
    JsonResponse,
    RemoteFile,
    ScanFinished,
    TaskKind,
    WorkerFailed,
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


def test_idle_announces_completion_exactly_once(
    deps: downloader.WorkerDeps,
) -> None:
    worker = downloader.Worker(deps)
    with patch.object(net, "get_json", return_value=_json([])):
        worker.run_once()
    with patch.object(deps.stop, "wait"):
        assert worker.run_once() is TaskKind.IDLE
        assert worker.run_once() is TaskKind.IDLE
    finished = [e for e in _drain(deps.events) if isinstance(e, ScanFinished)]
    assert len(finished) == 1


def test_the_board_is_rescanned_after_the_quiet_period(
    deps: downloader.WorkerDeps,
) -> None:
    """A finished sweep goes quiet, then polls again for new content."""
    worker = downloader.Worker(deps)
    with patch.object(net, "get_json", return_value=_json([])):
        worker.run_once()
        with patch.object(deps.stop, "wait"):
            assert worker.run_once() is TaskKind.IDLE
            with patch(
                "python_pkg.wsg_grabber.downloader.time.monotonic",
                return_value=time.monotonic() + IDLE_RESCAN_S + 1,
            ):
                assert worker.run_once() is TaskKind.IDLE
        # the quiet period has elapsed, so the next step walks the board again
        assert worker.run_once() is TaskKind.SCAN
    finished = [e for e in _drain(deps.events) if isinstance(e, ScanFinished)]
    assert len(finished) == 1


def test_rate_limiting_waits_between_requests(
    deps: downloader.WorkerDeps,
) -> None:
    worker = downloader.Worker(deps)
    listing = [{"threads": [{"no": 7, "last_modified": 100}]}]
    with (
        patch.object(
            net,
            "get_json",
            side_effect=[_json(listing), _json({"posts": []})],
        ),
        patch.object(deps.stop, "wait") as waited,
    ):
        worker.run_once()  # the first request is free
        worker.run_once()  # the second must be spaced out
    delays = [call.args[0] for call in waited.call_args_list if call.args]
    assert delays
    assert max(delays) <= 1.0


def test_run_reports_a_crash_and_closes_resources(
    deps: downloader.WorkerDeps,
) -> None:
    worker = downloader.Worker(deps)
    with patch.object(worker, "run_once", side_effect=RuntimeError("kaput")):
        worker.run()
    events = _drain(deps.events)
    assert any(
        isinstance(event, WorkerFailed) and event.message == "kaput" for event in events
    )
    cast("MagicMock", deps.session).close.assert_called_once()


def test_run_exits_cleanly_when_stopped(deps: downloader.WorkerDeps) -> None:
    deps.stop.set()
    worker = downloader.Worker(deps)
    worker.run()
    assert _drain(deps.events) == []
    cast("MagicMock", deps.session).close.assert_called_once()


@pytest.mark.timeout(10)
def test_start_runs_and_joins_a_real_thread(tmp_path: Path) -> None:
    """The one test that starts a thread; it must stop on demand."""
    incoming = tmp_path / "incoming"
    incoming.mkdir()
    stop = threading.Event()
    stop.set()

    def build() -> downloader.WorkerDeps:
        """Open the connection on the worker thread, which must own it."""
        return downloader.WorkerDeps(
            conn=db.open_index(tmp_path / "index.db"),
            session=MagicMock(),
            incoming=incoming,
            events=queue.SimpleQueue(),
            stop=stop,
            include_archive=False,
        )

    thread = downloader.start(build)
    thread.join(timeout=5)
    assert not thread.is_alive()
