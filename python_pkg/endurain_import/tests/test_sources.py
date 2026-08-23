"""Inbox scanning and the adb fallback.

The fallback is read-only with respect to the phone: screen-locker reads the
same directory as its screen-unlock gate, so nothing here may delete or
rewrite those files.
"""

from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

from python_pkg.endurain_import import sources


def test_inbox_lists_only_activity_files(tmp_path: Path) -> None:
    (tmp_path / "a.tcx").write_text("x")
    (tmp_path / "b.gpx").write_text("x")
    (tmp_path / "c.fit").write_text("x")
    (tmp_path / "notes.txt").write_text("x")
    names = {p.name for p in sources.inbox_files(tmp_path)}
    assert names == {"a.tcx", "b.gpx", "c.fit"}


def test_inbox_skips_processed_subdir(tmp_path: Path) -> None:
    (tmp_path / "processed").mkdir()
    (tmp_path / "processed" / "old.tcx").write_text("x")
    assert sources.inbox_files(tmp_path) == []


def test_missing_inbox_is_not_an_error(tmp_path: Path) -> None:
    assert sources.inbox_files(tmp_path / "nope") == []


def test_inbox_is_ordered_oldest_first(tmp_path: Path) -> None:
    first = tmp_path / "first.tcx"
    second = tmp_path / "second.tcx"
    first.write_text("x")
    second.write_text("x")
    import os

    os.utime(first, (1000, 1000))
    os.utime(second, (2000, 2000))
    assert [p.name for p in sources.inbox_files(tmp_path)] == [
        "first.tcx",
        "second.tcx",
    ]


def test_phone_attached_parses_adb_devices(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        sources,
        "_adb",
        lambda _a: (True, "List of devices attached\nABC123\tdevice\n"),
    )
    assert sources.phone_attached()


def test_phone_unauthorised_is_not_attached(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        sources,
        "_adb",
        lambda _a: (True, "List of devices attached\nABC123\tunauthorized\n"),
    )
    assert not sources.phone_attached()


def test_pull_skips_when_no_device(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(sources, "phone_attached", lambda: False)
    assert sources.pull_from_phone(tmp_path) == []


def test_pull_ignores_already_present_files(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(sources, "phone_attached", lambda: True)
    monkeypatch.setattr(sources, "_adb", lambda _a: (True, "RunnerUp_ts_Running.tcx\n"))
    (tmp_path / "RunnerUp_ts_Running.tcx").write_text("already here")
    assert sources.pull_from_phone(tmp_path) == []


def test_failed_pull_leaves_no_partial_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A half-transferred file must never look like a complete activity."""
    monkeypatch.setattr(sources, "phone_attached", lambda: True)

    def _adb(args: list[str]) -> tuple[bool, str]:
        if args[0] == "shell":
            return True, "RunnerUp_ts_Running.tcx\n"
        return False, "pull failed"

    monkeypatch.setattr(sources, "_adb", _adb)
    assert sources.pull_from_phone(tmp_path) == []
    assert list(tmp_path.iterdir()) == []


def test_adb_handles_missing_binary(monkeypatch: pytest.MonkeyPatch) -> None:
    """A machine with no adb reports 'no device', it does not crash the run."""

    def _boom(*_a: object, **_k: object) -> None:
        message = "adb not found"
        raise OSError(message)

    monkeypatch.setattr(subprocess, "run", _boom)
    ok, out = sources._adb(["devices"])
    assert not ok
    assert "adb not found" in out


def test_adb_handles_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    def _slow(*_a: object, **_k: object) -> None:
        raise subprocess.TimeoutExpired(cmd="adb", timeout=1)

    monkeypatch.setattr(subprocess, "run", _slow)
    ok, _ = sources._adb(["devices"])
    assert not ok


def test_adb_returns_output_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Proc:
        returncode = 0
        stdout = "out"
        stderr = ""

    monkeypatch.setattr(subprocess, "run", lambda *_a, **_k: _Proc())
    ok, out = sources._adb(["devices"])
    assert ok
    assert out == "out"


def test_phone_attached_false_when_adb_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sources, "_adb", lambda _a: (False, "boom"))
    assert not sources.phone_attached()


def test_pull_reports_unlistable_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(sources, "phone_attached", lambda: True)
    monkeypatch.setattr(sources, "_adb", lambda _a: (False, "no such dir"))
    assert sources.pull_from_phone(tmp_path) == []


def test_successful_pull_moves_into_place(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(sources, "phone_attached", lambda: True)

    def _adb(args: list[str]) -> tuple[bool, str]:
        if args[0] == "shell":
            return True, "RunnerUp_ts_Running.tcx\nnotes.txt\n"
        Path(args[2]).write_text("pulled")
        return True, ""

    monkeypatch.setattr(sources, "_adb", _adb)
    pulled = sources.pull_from_phone(tmp_path)
    assert [p.name for p in pulled] == ["RunnerUp_ts_Running.tcx"]
    assert (tmp_path / "RunnerUp_ts_Running.tcx").read_text() == "pulled"
    assert not list(tmp_path.glob(".*partial"))
