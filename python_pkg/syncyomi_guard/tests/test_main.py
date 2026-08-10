"""Tests for the CLI, whose exit code is the contract systemd reads.

The rule under test throughout: the guard fails closed. Anything it cannot
verify is a failure, because "I could not check, so everything is fine" is how
a degraded copy becomes the only copy.
"""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

import pytest

from python_pkg.syncyomi_guard.__main__ import main
from python_pkg.syncyomi_guard.store import load_baseline
from python_pkg.syncyomi_guard.tests.conftest import backup

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path


def _write_db(path: Path, blob: bytes) -> None:
    conn = sqlite3.connect(path)
    try:
        with conn:
            conn.execute("CREATE TABLE sync_data (id INTEGER PRIMARY KEY, data BLOB)")
            conn.execute("INSERT INTO sync_data (id, data) VALUES (1, ?)", (blob,))
    finally:
        conn.close()


def _args(tmp_path: Path, db: Path, *extra: str) -> Sequence[str]:
    return [
        "--db",
        str(db),
        "--state-dir",
        str(tmp_path / "state"),
        "--snapshot-dir",
        str(tmp_path / "snaps"),
        *extra,
    ]


@pytest.fixture(autouse=True)
def _no_notifications(monkeypatch: pytest.MonkeyPatch) -> None:
    """Never fire a real desktop notification from a test."""
    monkeypatch.setattr(
        "python_pkg.syncyomi_guard.__main__.shutil.which", lambda _: None
    )


def test_first_run_records_a_baseline_and_snapshot(tmp_path: Path) -> None:
    db = tmp_path / "syncyomi.db"
    _write_db(db, backup(manga_count=10, chapters_each=2, categories=3))

    assert main(_args(tmp_path, db)) == 0
    assert load_baseline(tmp_path / "state") is not None
    assert list((tmp_path / "snaps").glob("*.tachibk"))


def test_healthy_second_run_passes(tmp_path: Path) -> None:
    db = tmp_path / "syncyomi.db"
    _write_db(db, backup(manga_count=10, chapters_each=2, categories=3))
    assert main(_args(tmp_path, db)) == 0
    assert main(_args(tmp_path, db)) == 0


def test_collapse_fails_and_preserves_the_good_snapshot(tmp_path: Path) -> None:
    """The 2026-08-09 scenario, end to end through the binary."""
    db = tmp_path / "syncyomi.db"
    _write_db(db, backup(manga_count=100, chapters_each=5, categories=8))
    assert main(_args(tmp_path, db)) == 0

    good = sorted((tmp_path / "snaps").glob("*.tachibk"))
    assert len(good) == 1
    good_bytes = good[0].read_bytes()

    # The library collapses to a sources-only stub, exactly as it did that night.
    db.unlink()
    _write_db(db, backup(manga_count=0, sources=2))

    assert main(_args(tmp_path, db)) == 1

    after = sorted((tmp_path / "snaps").glob("*.tachibk"))
    assert len(after) == 1, "a collapsed payload must not be snapshotted"
    assert after[0].read_bytes() == good_bytes
    baseline = load_baseline(tmp_path / "state")
    assert baseline is not None
    assert baseline.manga == 100, "baseline must not absorb the collapse"


def test_accept_overrides_a_deliberate_purge(tmp_path: Path) -> None:
    db = tmp_path / "syncyomi.db"
    _write_db(db, backup(manga_count=100, chapters_each=2, categories=4))
    assert main(_args(tmp_path, db)) == 0

    db.unlink()
    _write_db(db, backup(manga_count=1, sources=1))

    assert main(_args(tmp_path, db, "--accept")) == 0
    baseline = load_baseline(tmp_path / "state")
    assert baseline is not None
    assert baseline.manga == 1


def test_no_snapshot_checks_without_writing(tmp_path: Path) -> None:
    db = tmp_path / "syncyomi.db"
    _write_db(db, backup(manga_count=5, chapters_each=1))
    assert main(_args(tmp_path, db, "--no-snapshot")) == 0
    assert not (tmp_path / "snaps").exists()
    assert load_baseline(tmp_path / "state") is None


def test_missing_database_exits_nonzero(tmp_path: Path) -> None:
    """Fail closed rather than reporting a pass for an unreadable database."""
    assert main(_args(tmp_path, tmp_path / "absent.db")) == 1


def test_undecodable_payload_exits_nonzero(tmp_path: Path) -> None:
    db = tmp_path / "syncyomi.db"
    _write_db(db, b"\xff\xff\xff not protobuf")
    assert main(_args(tmp_path, db)) == 1


def test_invalid_threshold_exits_nonzero(tmp_path: Path) -> None:
    db = tmp_path / "syncyomi.db"
    _write_db(db, backup(manga_count=1))
    assert main(_args(tmp_path, db, "--max-drop", "5")) == 1


def test_collapse_message_names_the_loss(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db = tmp_path / "syncyomi.db"
    _write_db(db, backup(manga_count=50, chapters_each=2, categories=6))
    main(_args(tmp_path, db))
    capsys.readouterr()

    db.unlink()
    _write_db(db, backup(manga_count=50, chapters_each=2, categories=0))
    main(_args(tmp_path, db))

    err = capsys.readouterr().err
    assert "COLLAPSED" in err
    assert "categories went from 6 to 0" in err


def test_report_handles_a_collapse_without_a_baseline(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Defensive branch: ``compare`` never returns this, but ``_report`` must cope.

    A COLLAPSED verdict always carries the baseline it was measured against, so
    this shape is unreachable through ``main``. It is covered directly so the
    guard cannot crash while reporting the one thing it exists to report.
    """
    from python_pkg.syncyomi_guard.__main__ import _report
    from python_pkg.syncyomi_guard.payload import PayloadStats
    from python_pkg.syncyomi_guard.verdict import Status, Verdict

    stats = PayloadStats(
        size_bytes=1,
        manga=0,
        categories=0,
        chapters=0,
        sources=0,
    )
    _report(
        Verdict(
            status=Status.COLLAPSED,
            reason="synthetic",
            current=stats,
            previous=None,
        ),
    )
    err = capsys.readouterr().err
    assert "COLLAPSED" in err
    assert "previous:" not in err


def test_notification_is_attempted_on_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failure should reach the desktop, but must not depend on it."""
    calls: list[list[str]] = []
    monkeypatch.setattr(
        "python_pkg.syncyomi_guard.__main__.shutil.which",
        lambda _: "/usr/bin/notify-send",
    )
    monkeypatch.setattr(
        "python_pkg.syncyomi_guard.__main__.subprocess.run",
        lambda cmd, **_: calls.append(cmd),
    )
    assert main(_args(tmp_path, tmp_path / "absent.db")) == 1
    assert calls
    assert "notify-send" in calls[0][0]


def test_notification_failure_does_not_mask_the_verdict(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def explode(*_: object, **__: object) -> None:
        msg = "no session bus"
        raise OSError(msg)

    monkeypatch.setattr(
        "python_pkg.syncyomi_guard.__main__.shutil.which",
        lambda _: "/usr/bin/notify-send",
    )
    monkeypatch.setattr("python_pkg.syncyomi_guard.__main__.subprocess.run", explode)
    assert main(_args(tmp_path, tmp_path / "absent.db")) == 1
