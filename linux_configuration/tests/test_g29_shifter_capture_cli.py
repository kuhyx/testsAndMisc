"""Tests for g29_shifter_capture.py: the ``record`` loop and the CLI entry."""

from __future__ import annotations

import io
from typing import TYPE_CHECKING

import g29_shifter_capture as gsc
import pytest

if TYPE_CHECKING:
    from conftest import G29Reports

if TYPE_CHECKING:
    from pathlib import Path

TOP_Y = 200
X_LEFT = 60


class TestRecord:
    """``record`` streams xxd lines and survives the device re-binding."""

    @staticmethod
    def _clock(monkeypatch: pytest.MonkeyPatch, zeros: int) -> None:
        """Make ``time.monotonic`` return 0 for ``zeros`` calls, then 99."""
        calls = {"n": 0}

        def monotonic() -> float:
            calls["n"] += 1
            return 0.0 if calls["n"] <= zeros else 99.0

        monkeypatch.setattr(gsc.time, "monotonic", monotonic)
        monkeypatch.setattr(gsc.time, "sleep", lambda _: None)

    def test_writes_every_report_it_reads(
        self, g29: type[G29Reports], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        device = tmp_path / "hidraw"
        device.write_bytes(bytes(g29.raw_report(gears=0x01, x=X_LEFT, y=TOP_Y)) * 3)
        out = tmp_path / "capture.txt"
        self._clock(monkeypatch, zeros=6)  # deadline, outer, 3 reads, short read

        assert gsc.record(1.0, str(device), out) == 0

        reports = list(gsc.parse(out.read_text().splitlines(keepends=True)))
        assert len(reports) == 3
        assert reports[0].gate == "1st"

    def test_stops_mid_device_when_the_deadline_passes(
        self, g29: type[G29Reports], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        device = tmp_path / "hidraw"
        device.write_bytes(bytes(g29.raw_report(gears=0x01, x=X_LEFT, y=TOP_Y)) * 3)
        out = tmp_path / "capture.txt"
        self._clock(monkeypatch, zeros=4)  # deadline, outer, two reads, then expired

        assert gsc.record(1.0, str(device), out) == 0

        # Stopped on the clock with a report still unread, not at end of device.
        assert len(list(gsc.parse(out.read_text().splitlines(keepends=True)))) == 2

    def test_reopens_after_an_os_error(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        out = tmp_path / "capture.txt"
        self._clock(monkeypatch, zeros=2)  # deadline, one failing attempt

        assert gsc.record(1.0, str(tmp_path / "missing"), out) == 0

        assert "reopening" in capsys.readouterr().err
        assert out.read_text() == ""


class TestMain:
    """``main`` wires the CLI to the grader and optionally to the recorder."""

    def test_grades_a_file(
        self, g29: type[G29Reports], tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        capture = tmp_path / "capture.txt"
        capture.write_text(
            g29.xxd_line(gears=0x01, x=X_LEFT, y=TOP_Y) * (gsc.MIN_DWELL + 1)
        )
        assert gsc.main([str(capture)]) == 0
        assert "0 missed" in capsys.readouterr().out

    def test_reads_stdin(
        self, g29: type[G29Reports], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            gsc.sys, "stdin", io.StringIO(g29.xxd_line(x=X_LEFT, y=TOP_Y))
        )
        assert gsc.main(["-"]) == 0

    def test_records_first_when_asked(
        self, g29: type[G29Reports], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        device = tmp_path / "hidraw"
        device.write_bytes(bytes(g29.raw_report(gears=0x01, x=X_LEFT, y=TOP_Y)))
        capture = tmp_path / "capture.txt"
        TestRecord._clock(monkeypatch, zeros=4)  # deadline, outer, one read, short read
        assert gsc.main([str(capture), "--record", "1", "--device", str(device)]) == 0
        assert capture.read_text().count("\n") == 1
