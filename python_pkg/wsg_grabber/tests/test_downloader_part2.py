"""More tests for the background worker.

Split from test_downloader.py to stay under this repo's 500-line-per-file cap;
the fixtures are duplicated because each test module must stand alone.
"""

from __future__ import annotations

import queue
import threading
import time
from typing import TYPE_CHECKING, cast
from unittest.mock import MagicMock, patch

import pytest

from python_pkg.wsg_grabber import db, downloader, net, store, store_threads
from python_pkg.wsg_grabber.constants import IDLE_RESCAN_S, THREADS_URL
from python_pkg.wsg_grabber.models import (
    DownloadEvent,
    DownloadResult,
    JsonResponse,
    Outcome,
    RemoteFile,
    ScanFinished,
    TaskKind,
    ThreadRef,
    WorkerFailed,
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


def test_download_progress_is_persisted(deps: downloader.WorkerDeps) -> None:
    worker = downloader.Worker(deps)
    store.record_files(deps.conn, [_remote()])

    def fake_download(_session: object, transfer: net.Transfer) -> DownloadResult:
        assert transfer.on_progress is not None
        transfer.on_progress(7)
        return DownloadResult(outcome=Outcome.ABORTED, bytes_done=7)

    with patch.object(net, "download", side_effect=fake_download):
        worker.run_once()
    assert deps.conn.execute("SELECT bytes_done FROM files").fetchone()[0] == 7


def test_claim_losing_a_race_is_a_no_op(deps: downloader.WorkerDeps) -> None:
    worker = downloader.Worker(deps)
    store.record_files(deps.conn, [_remote()])
    with (
        patch.object(store, "claim_next", return_value=None),
        patch.object(
            net,
            "download",
        ) as never,
    ):
        worker._download_one()
    never.assert_not_called()


def test_deleted_upstream_files_are_written_off(
    deps: downloader.WorkerDeps,
) -> None:
    worker = downloader.Worker(deps)
    store.record_files(deps.conn, [_remote()])
    thread = {"posts": [{"no": 1, "md5": _MD5, "filedeleted": 1}]}
    # Driven directly: with a file queued, run_once would always pick DOWNLOAD
    # over SCAN, so the thread fetch under test would never happen.
    with patch.object(net, "get_json", return_value=_json(thread)):
        worker._fetch_thread(ThreadRef(7, 100))
    assert store.counts(deps.conn)[FileState.GONE.value] == 1
    assert store.pending_downloads(deps.conn) == 0


def test_an_already_downloaded_file_survives_upstream_deletion(
    deps: downloader.WorkerDeps,
) -> None:
    """Once the bytes are ours, the post being deleted is irrelevant."""
    worker = downloader.Worker(deps)
    store.record_files(deps.conn, [_remote()])
    store.mark_downloaded(deps.conn, _MD5, "1-x.webm")
    thread = {"posts": [{"no": 1, "md5": _MD5, "filedeleted": 1}]}
    with patch.object(net, "get_json", return_value=_json(thread)):
        worker._fetch_thread(ThreadRef(7, 100))
    assert store.state_of(deps.conn, _MD5) is FileState.READY


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
