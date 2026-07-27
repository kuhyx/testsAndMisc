"""Tests for the background worker.

Every case drives ``run_once`` directly. No real thread runs and no socket is
opened, so the suite stays deterministic and cannot leak either.
"""

from __future__ import annotations

import queue
import threading
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from python_pkg.wsg_grabber import db, downloader, net, store, store_threads
from python_pkg.wsg_grabber.models import (
    Downloaded,
    DownloadEvent,
    DownloadResult,
    FileReady,
    Indexed,
    JsonResponse,
    Outcome,
    RemoteFile,
    TaskKind,
    ThreadRef,
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


def test_first_step_reads_the_thread_list(deps: downloader.WorkerDeps) -> None:
    worker = downloader.Worker(deps)
    payload = [{"threads": [{"no": 7, "last_modified": 100}]}]
    with patch.object(net, "get_json", return_value=_json(payload)):
        assert worker.run_once() is TaskKind.SCAN


def test_scan_then_fetch_records_files(deps: downloader.WorkerDeps) -> None:
    worker = downloader.Worker(deps)
    listing = [{"threads": [{"no": 7, "last_modified": 100}]}]
    thread = {
        "posts": [
            {
                "no": 1,
                "tim": 1,
                "ext": ".webm",
                "md5": _MD5,
                "fsize": 11,
                "w": 4,
                "h": 3,
                "filename": "clip",
            },
        ],
    }
    with patch.object(
        net,
        "get_json",
        side_effect=[_json(listing), _json(thread, last_modified="stamp")],
    ):
        worker.run_once()
        worker.run_once()

    assert store.known_md5s(deps.conn) == {_MD5}
    assert store_threads.known_threads(deps.conn) == {7: 100}
    assert store_threads.http_last_modified(deps.conn, 7) == "stamp"
    assert any(isinstance(event, Indexed) for event in _drain(deps.events))


def test_an_unchanged_thread_costs_only_a_304(deps: downloader.WorkerDeps) -> None:
    worker = downloader.Worker(deps)
    store_threads.record_thread(deps.conn, ThreadRef(7, 50), "old-stamp")
    listing = [{"threads": [{"no": 7, "last_modified": 100}]}]
    with patch.object(
        net,
        "get_json",
        side_effect=[_json(listing), _json(None, not_modified=True)],
    ) as fake:
        worker.run_once()
        worker.run_once()
    assert fake.call_args.args[2] == "old-stamp"
    assert store_threads.known_threads(deps.conn) == {7: 100}
    assert store.known_md5s(deps.conn) == set()


def test_a_vanished_thread_is_marked_gone(deps: downloader.WorkerDeps) -> None:
    worker = downloader.Worker(deps)
    listing = [{"threads": [{"no": 7, "last_modified": 100}]}]
    with patch.object(
        net,
        "get_json",
        side_effect=[_json(listing), _json(None, not_found=True)],
    ):
        worker.run_once()
        worker.run_once()
    row = deps.conn.execute("SELECT status FROM threads WHERE thread_no=7").fetchone()
    assert row["status"] == "gone"


def test_archive_threads_are_included_when_enabled(
    deps: downloader.WorkerDeps,
) -> None:
    deps.include_archive = True
    worker = downloader.Worker(deps)
    with patch.object(
        net,
        "get_json",
        side_effect=[
            _json([{"threads": [{"no": 7, "last_modified": 1}]}]),
            _json([88]),
        ],
    ):
        worker.run_once()
    with patch.object(net, "get_json", side_effect=[_json({"posts": []})]) as fake:
        worker.run_once()
    assert "/thread/" in fake.call_args.args[1]


def test_a_board_without_an_archive_is_tolerated(
    deps: downloader.WorkerDeps,
) -> None:
    deps.include_archive = True
    worker = downloader.Worker(deps)
    with patch.object(
        net,
        "get_json",
        side_effect=[_json([]), _json(None, not_found=True)],
    ):
        assert worker.run_once() is TaskKind.SCAN


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
