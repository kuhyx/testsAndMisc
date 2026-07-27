"""Tests for the typed index operations."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from python_pkg.wsg_grabber import db, store, store_threads, store_verdicts
from python_pkg.wsg_grabber.models import RemoteFile, ThreadRef
from python_pkg.wsg_grabber.states import CLAIMABLE, FileState

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path
    import sqlite3

_EXPECTED_CLAIMABLE_STATES = 3


@pytest.fixture
def conn(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    """Open a migrated index for one test and close it afterwards.

    Closing matters: pytest runs with ``filterwarnings = ["error", ...]`` and a
    leaked connection surfaces as a ResourceWarning, i.e. a test failure.

    Args:
        tmp_path: Per-test temporary directory.

    Yields:
        sqlite3.Connection: Ready connection.
    """
    connection = db.open_index(tmp_path / "index.db")
    try:
        yield connection
    finally:
        connection.close()


def _file(md5: str = "AAAA", tim: int = 111, thread_no: int = 9) -> RemoteFile:
    """Build a RemoteFile with sensible defaults.

    Args:
        md5: Identity.
        tim: CDN filename stem.
        thread_no: Owning thread.

    Returns:
        RemoteFile: Test fixture value.
    """
    return RemoteFile(
        md5=md5,
        tim=tim,
        ext=".webm",
        orig_name="clip",
        fsize=1234,
        width=480,
        height=360,
        thread_no=thread_no,
        post_no=tim,
    )


def test_claimable_placeholder_count_matches_the_state_set() -> None:
    """The SQL spells out one '?' per claimable state; keep them in step."""
    assert len(CLAIMABLE) == _EXPECTED_CLAIMABLE_STATES
    assert len(store.claimable_values()) == _EXPECTED_CLAIMABLE_STATES


def test_local_name_ignores_the_poster_supplied_filename() -> None:
    name = store.local_name("ab/cd+ef==", 555, ".webm")
    assert name.startswith("555-")
    assert name.endswith(".webm")
    assert "/" not in name
    assert "+" not in name


def test_record_files_counts_only_new_rows(conn: sqlite3.Connection) -> None:
    assert store.record_files(conn, [_file("A"), _file("B", tim=2)]) == 2
    assert store.record_files(conn, [_file("B", tim=2), _file("C", tim=3)]) == 1
    assert store.known_md5s(conn) == {"A", "B", "C"}


def test_record_files_with_nothing_to_do(conn: sqlite3.Connection) -> None:
    assert store.record_files(conn, []) == 0


def test_a_repost_of_identical_bytes_never_becomes_a_second_row(
    conn: sqlite3.Connection,
) -> None:
    """Same md5 in another thread must not cost a second download."""
    store.record_files(conn, [_file("SAME", tim=1, thread_no=100)])
    added = store.record_files(conn, [_file("SAME", tim=999, thread_no=200)])
    assert added == 0
    assert store.pending_downloads(conn) == 1


def test_claim_next_takes_the_oldest_and_marks_it_in_flight(
    conn: sqlite3.Connection,
) -> None:
    store.record_files(conn, [_file("A", tim=1)])
    claimed = store.claim_next(conn)
    assert claimed is not None
    assert claimed.md5 == "A"
    assert store.attempts_for(conn, "A") == 1
    assert store.counts(conn)[FileState.DOWNLOADING.value] == 1


def test_claim_next_returns_none_when_idle(conn: sqlite3.Connection) -> None:
    assert store.claim_next(conn) is None


def test_claim_next_rolls_back_on_failure() -> None:
    """A mid-transaction failure must not leave the claim half-applied.

    ``sqlite3.Connection.execute`` is read-only so it cannot be patched on a
    real connection; a mock stands in purely to inject the failure.
    """
    fake = MagicMock()
    # BEGIN IMMEDIATE, then the SELECT blows up, then ROLLBACK must still run.
    fake.execute.side_effect = [MagicMock(), RuntimeError("simulated"), MagicMock()]

    with pytest.raises(RuntimeError, match="simulated"):
        store.claim_next(fake)

    executed = [call.args[0] for call in fake.execute.call_args_list]
    assert executed[0] == "BEGIN IMMEDIATE"
    assert executed[-1] == "ROLLBACK"


def test_attempts_for_unknown_file_is_zero(conn: sqlite3.Connection) -> None:
    assert store.attempts_for(conn, "nope") == 0


def test_set_state_records_the_error(conn: sqlite3.Connection) -> None:
    store.record_files(conn, [_file("A")])
    store.set_state(conn, "A", FileState.GONE, error="404")
    row = conn.execute("SELECT state, last_error FROM files").fetchone()
    assert row["state"] == FileState.GONE.value
    assert row["last_error"] == "404"


def test_mark_downloaded_makes_the_file_reviewable(
    conn: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    store.record_files(conn, [_file("A", tim=42)])
    store.mark_downloaded(conn, "A", "42-x.webm")
    items = store.ready_items(conn, tmp_path)
    assert len(items) == 1
    assert items[0].md5 == "A"
    assert items[0].path == tmp_path / "42-x.webm"
    assert items[0].orig_name == "clip.webm"


def test_ready_items_is_empty_before_any_download(
    conn: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    store.record_files(conn, [_file("A")])
    assert store.ready_items(conn, tmp_path) == []


def test_record_progress_persists_partial_bytes(conn: sqlite3.Connection) -> None:
    store.record_files(conn, [_file("A")])
    store.record_progress(conn, "A", 4096)
    assert conn.execute("SELECT bytes_done FROM files").fetchone()[0] == 4096


def test_record_verdict_is_terminal_and_stamps_the_time(
    conn: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    store.record_files(conn, [_file("A")])
    store.mark_downloaded(conn, "A", "a.webm")
    store_verdicts.record_verdict(conn, "A", FileState.PASSED)
    assert store.ready_items(conn, tmp_path) == []
    assert conn.execute("SELECT reviewed_at FROM files").fetchone()[0] is not None
    assert store.pending_downloads(conn) == 0


def test_a_reviewed_file_is_still_remembered_so_it_never_returns(
    conn: sqlite3.Connection,
) -> None:
    store.record_files(conn, [_file("A")])
    store_verdicts.record_verdict(conn, "A", FileState.PASSED)
    assert "A" in store.known_md5s(conn)
    assert store.record_files(conn, [_file("A")]) == 0


def test_reset_in_flight_recovers_an_interrupted_download(
    conn: sqlite3.Connection,
) -> None:
    store.record_files(conn, [_file("A")])
    store.claim_next(conn)
    assert store.reset_in_flight(conn) == 1
    assert store.pending_downloads(conn) == 1
    assert store.reset_in_flight(conn) == 0


def test_counts_reports_every_state_and_a_total(conn: sqlite3.Connection) -> None:
    store.record_files(conn, [_file("A"), _file("B", tim=2)])
    store.set_state(conn, "A", FileState.GONE)
    result = store.counts(conn)
    assert result["total"] == 2
    assert result[FileState.GONE.value] == 1
    assert result[FileState.NEW.value] == 1


def test_thread_bookkeeping_round_trip(conn: sqlite3.Connection) -> None:
    stamp = "Mon, 27 Jul 2026 08:00:00 GMT"
    store_threads.record_thread(conn, ThreadRef(7, 1000), stamp)
    assert store_threads.known_threads(conn) == {7: 1000}
    stamp = "Mon, 27 Jul 2026 08:00:00 GMT"
    assert store_threads.http_last_modified(conn, 7) == stamp

    store_threads.record_thread(conn, ThreadRef(7, 2000), None)
    assert store_threads.known_threads(conn) == {7: 2000}
    stamp = "Mon, 27 Jul 2026 08:00:00 GMT"
    assert store_threads.http_last_modified(conn, 7) == stamp


def test_http_last_modified_absent_cases(conn: sqlite3.Connection) -> None:
    assert store_threads.http_last_modified(conn, 404) is None
    store_threads.record_thread(conn, ThreadRef(8, 1), None)
    assert store_threads.http_last_modified(conn, 8) is None


def test_mark_thread_gone(conn: sqlite3.Connection) -> None:
    store_threads.record_thread(conn, ThreadRef(7, 1000), None)
    store_threads.mark_thread_gone(conn, 7)
    row = conn.execute("SELECT status FROM threads WHERE thread_no = 7").fetchone()
    assert row["status"] == "gone"
