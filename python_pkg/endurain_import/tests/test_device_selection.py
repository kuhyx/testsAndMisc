"""Which phone the adb fallback pulls from.

Ambiguity is settled by configuration, never by guessing: the old check
returned true for ANY attached device, after which every call failed with
"more than one device/emulator" as a warning on a path nobody watches.
"""

from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

from python_pkg.endurain_import import sources


def _devices(*serials: str) -> str:
    body = "".join(f"{s}\tdevice\n" for s in serials)
    return f"List of devices attached\n{body}"


def test_single_device_is_selected_without_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(sources.ADB_SERIAL_ENV, raising=False)
    monkeypatch.setattr(sources, "_adb", lambda _a, _s=None: (True, _devices("ONE")))
    assert sources.resolve_serial() == "ONE"


def test_no_devices_resolves_to_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(sources.ADB_SERIAL_ENV, raising=False)
    monkeypatch.setattr(sources, "_adb", lambda _a, _s=None: (True, _devices()))
    assert sources.resolve_serial() is None


def test_several_devices_without_a_pin_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Two devices must not silently become 'adb picks whichever it likes'."""
    monkeypatch.delenv(sources.ADB_SERIAL_ENV, raising=False)
    monkeypatch.setattr(
        sources, "_adb", lambda _a, _s=None: (True, _devices("ONE", "TWO"))
    )
    assert sources.resolve_serial() is None


def test_pinned_serial_wins_when_several_are_attached(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(sources.ADB_SERIAL_ENV, "TWO")
    monkeypatch.setattr(
        sources, "_adb", lambda _a, _s=None: (True, _devices("ONE", "TWO"))
    )
    assert sources.resolve_serial() == "TWO"


def test_pinned_serial_that_is_absent_resolves_to_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(sources.ADB_SERIAL_ENV, "GONE")
    monkeypatch.setattr(sources, "_adb", lambda _a, _s=None: (True, _devices("ONE")))
    assert sources.resolve_serial() is None


def test_blank_pin_falls_back_to_the_single_device(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(sources.ADB_SERIAL_ENV, "   ")
    monkeypatch.setattr(sources, "_adb", lambda _a, _s=None: (True, _devices("ONE")))
    assert sources.resolve_serial() == "ONE"


def test_devices_output_without_tabs_is_ignored(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(sources.ADB_SERIAL_ENV, raising=False)
    monkeypatch.setattr(
        sources,
        "_adb",
        lambda _a, _s=None: (True, "List of devices attached\n* daemon started *\n"),
    )
    assert sources.attached_serials() == []


def test_serial_is_passed_to_every_adb_call(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Without -s, a second attached device breaks every call with a warning."""
    seen: list[list[str]] = []

    def _adb(args: list[str], serial: str | None = None) -> tuple[bool, str]:
        seen.append(["-s", serial or "", *args])
        if args[0] == "shell":
            return True, "RunnerUp_ts_Running.tcx\n"
        Path(args[2]).write_text("pulled")
        return True, ""

    monkeypatch.setattr(sources, "resolve_serial", lambda: "PIXEL")
    monkeypatch.setattr(sources, "_adb", _adb)
    assert len(sources.pull_from_phone(tmp_path)) == 1
    assert all(call[1] == "PIXEL" for call in seen)


def test_adb_builds_argv_with_the_serial(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, list[str]] = {}

    class _Proc:
        returncode = 0
        stdout = "ok"
        stderr = ""

    def _run(argv: list[str], **_kwargs: object) -> _Proc:
        captured["argv"] = argv
        return _Proc()

    monkeypatch.setattr(subprocess, "run", _run)
    sources._adb(["shell", "ls"], "PIXEL")
    assert captured["argv"][1:4] == ["-s", "PIXEL", "shell"]
