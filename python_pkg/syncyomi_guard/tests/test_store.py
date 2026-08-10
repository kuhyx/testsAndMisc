"""Tests for reading the payload and keeping snapshots.

Two behaviours here are load-bearing and easy to regress: the database is
opened without taking a lock, and pruning never deletes more than it should.
"""

from __future__ import annotations

import gzip
import sqlite3
from typing import TYPE_CHECKING

import pytest

from python_pkg.syncyomi_guard.payload import PayloadError, PayloadStats
from python_pkg.syncyomi_guard.store import (
    StoreError,
    latest_snapshot,
    load_baseline,
    read_payload,
    read_snapshot,
    save_baseline,
    write_snapshot,
)

if TYPE_CHECKING:
    from datetime import datetime
    from pathlib import Path

_STATS = PayloadStats(
    size_bytes=100,
    manga=10,
    categories=2,
    chapters=30,
    sources=3,
)


def _make_db(path: Path, blob: object) -> None:
    """Create a minimal SyncYomi-shaped database holding ``blob``."""
    conn = sqlite3.connect(path)
    try:
        with conn:
            conn.execute("CREATE TABLE sync_data (id INTEGER PRIMARY KEY, data BLOB)")
            conn.execute("INSERT INTO sync_data (id, data) VALUES (1, ?)", (blob,))
    finally:
        conn.close()


def test_reads_the_payload_blob(tmp_path: Path) -> None:
    db = tmp_path / "syncyomi.db"
    _make_db(db, b"payload-bytes")
    assert read_payload(db) == b"payload-bytes"


def test_missing_database_is_an_error_not_an_empty_payload(tmp_path: Path) -> None:
    """Fail closed: a missing database must never read as "nothing to worry about"."""
    with pytest.raises(StoreError, match="no SyncYomi database"):
        read_payload(tmp_path / "absent.db")


def test_database_without_the_table_is_an_error(tmp_path: Path) -> None:
    db = tmp_path / "empty.db"
    conn = sqlite3.connect(db)
    try:
        with conn:
            conn.execute("CREATE TABLE unrelated (id INTEGER)")
    finally:
        conn.close()
    with pytest.raises(StoreError, match="cannot read"):
        read_payload(db)


def test_database_with_no_rows_is_an_error(tmp_path: Path) -> None:
    db = tmp_path / "norows.db"
    conn = sqlite3.connect(db)
    try:
        with conn:
            conn.execute("CREATE TABLE sync_data (id INTEGER PRIMARY KEY, data BLOB)")
    finally:
        conn.close()
    with pytest.raises(StoreError, match="no sync_data row"):
        read_payload(db)


def test_unopenable_database_is_an_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A connect-time failure must surface, not propagate as a raw sqlite error."""
    db = tmp_path / "syncyomi.db"
    _make_db(db, b"payload")

    def refuse(*_: object, **__: object) -> object:
        msg = "unable to open database file"
        raise sqlite3.OperationalError(msg)

    monkeypatch.setattr(
        "python_pkg.syncyomi_guard.store.sqlite3.connect",
        refuse,
    )
    with pytest.raises(StoreError, match="cannot read"):
        read_payload(db)


def test_non_blob_payload_is_an_error(tmp_path: Path) -> None:
    db = tmp_path / "text.db"
    _make_db(db, "not bytes")
    with pytest.raises(StoreError, match="expected bytes"):
        read_payload(db)


def test_reading_does_not_lock_the_database(tmp_path: Path) -> None:
    """The guard runs against a database the container is writing.

    An exclusive read would make the guard a cause of the very ``SQLITE_BUSY``
    class of failure it exists to detect.
    """
    db = tmp_path / "syncyomi.db"
    _make_db(db, b"payload")
    writer = sqlite3.connect(db)
    try:
        writer.execute("BEGIN IMMEDIATE")
        writer.execute("UPDATE sync_data SET data = ? WHERE id = 1", (b"changed",))
        assert read_payload(db) == b"payload"
        writer.rollback()
    finally:
        writer.close()


def test_baseline_round_trips(tmp_path: Path) -> None:
    save_baseline(tmp_path, _STATS)
    assert load_baseline(tmp_path) == _STATS


def test_absent_baseline_is_none(tmp_path: Path) -> None:
    assert load_baseline(tmp_path) is None


@pytest.mark.parametrize(
    "content",
    ["not json at all", '{"manga": 1}', '{"size_bytes": "x"}', "[]"],
)
def test_corrupt_baseline_reads_as_absent(tmp_path: Path, content: str) -> None:
    """A damaged state file must re-baseline loudly, not crash the timer."""
    (tmp_path / "last_known_good.json").write_text(content, encoding="utf-8")
    assert load_baseline(tmp_path) is None


def test_snapshot_is_a_restorable_tachibk(tmp_path: Path) -> None:
    """The snapshot must be exactly what the app restores from."""
    path = write_snapshot(tmp_path, b"library-bytes", keep=5)
    assert path.suffix == ".tachibk"
    assert gzip.decompress(path.read_bytes()) == b"library-bytes"
    assert read_snapshot(path) == b"library-bytes"


def test_snapshot_pruning_keeps_the_newest(tmp_path: Path) -> None:
    from datetime import UTC, datetime

    def at(day: int) -> datetime:
        return datetime(2026, 8, day, 12, 0, tzinfo=UTC)

    for day in range(1, 6):
        write_snapshot(tmp_path, f"day{day}".encode(), keep=3, now=at(day))

    remaining = sorted(p.name for p in tmp_path.glob("*.tachibk"))
    assert len(remaining) == 3
    assert "2026-08-05" in remaining[-1]
    assert read_snapshot(tmp_path / remaining[-1]) == b"day5"


def test_two_snapshots_in_the_same_second_do_not_overwrite(tmp_path: Path) -> None:
    """Second-granular timestamps must not silently collapse two snapshots.

    Overwriting would quietly keep fewer than ``keep`` snapshots, and in the
    worst case replace a good library with a stub written a fraction of a
    second later — the exact loss this package exists to prevent.
    """
    from datetime import UTC, datetime

    same_second = datetime(2026, 8, 9, 23, 45, 30, tzinfo=UTC)
    first = write_snapshot(tmp_path, b"good-library", keep=14, now=same_second)
    second = write_snapshot(tmp_path, b"degraded-stub", keep=14, now=same_second)

    assert first != second
    assert read_snapshot(first) == b"good-library"
    assert read_snapshot(second) == b"degraded-stub"
    assert len(list(tmp_path.glob("*.tachibk"))) == 2


def test_pruning_never_deletes_a_hand_named_recovery_file(tmp_path: Path) -> None:
    """Regression guard for a real near-miss.

    ``syncyomi_recovered_2026-08-09.tachibk`` was the only surviving copy of a
    2182-manga library, rebuilt from the SQLite WAL. A ``syncyomi_*.tachibk``
    prune glob would have matched and deleted it.
    """
    from datetime import UTC, datetime

    precious = tmp_path / "syncyomi_recovered_2026-08-09.tachibk"
    precious.write_bytes(b"irreplaceable")

    for day in range(1, 6):
        write_snapshot(
            tmp_path,
            b"routine",
            keep=1,
            now=datetime(2026, 8, day, tzinfo=UTC),
        )

    assert precious.exists()
    assert precious.read_bytes() == b"irreplaceable"


def test_keep_must_be_positive(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="keep must be"):
        write_snapshot(tmp_path, b"x", keep=0)


def test_latest_snapshot_reports_none_when_empty(tmp_path: Path) -> None:
    assert latest_snapshot(tmp_path) is None


def test_latest_snapshot_finds_the_newest(tmp_path: Path) -> None:
    from datetime import UTC, datetime

    write_snapshot(tmp_path, b"old", keep=9, now=datetime(2026, 8, 1, tzinfo=UTC))
    write_snapshot(tmp_path, b"new", keep=9, now=datetime(2026, 8, 9, tzinfo=UTC))
    newest = latest_snapshot(tmp_path)
    assert newest is not None
    assert read_snapshot(newest) == b"new"


def test_unreadable_snapshot_is_an_error(tmp_path: Path) -> None:
    bad = tmp_path / "syncyomi_broken.tachibk"
    bad.write_bytes(b"not gzip")
    with pytest.raises(PayloadError, match="cannot read snapshot"):
        read_snapshot(bad)
