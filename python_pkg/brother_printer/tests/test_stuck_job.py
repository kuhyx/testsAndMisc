"""Tests for brother_printer._stuck_job - stalled jobs and orphaned backends.

/proc, ipptool, lpstat, time and os.kill are all patched: nothing here reads
the live process table, talks to CUPS, sleeps, or signals a real process.
"""

from __future__ import annotations

from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from python_pkg.brother_printer import _stuck_job
from python_pkg.brother_printer._stuck_job import (
    StuckJob,
    detect_stuck_job,
    find_backend_pids,
    flag_stuck_job,
    kill_backend,
    offer_backend_kill,
)
from python_pkg.brother_printer.constants import (
    DERIVED_BACKEND_ORPHANED,
    DERIVED_JOB_STALLED,
)
from python_pkg.brother_printer.data_classes import USBResult

if TYPE_CHECKING:
    import pytest

MOD = "python_pkg.brother_printer._stuck_job"


def _proc(tmp_path: Path, pid: str, cmdline: bytes | None) -> None:
    """Create a fake /proc/<pid>; cmdline None means it is unreadable."""
    entry = tmp_path / pid
    entry.mkdir()
    if cmdline is not None:
        (entry / "cmdline").write_bytes(cmdline)


class TestFindBackendPids:
    def test_maps_job_id_to_pid(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _proc(tmp_path, "101", b"usb://Brother/HL-1110\x00105\x00kuhy\x00")
        _proc(tmp_path, "102", b"/usr/bin/gs\x00-dQUIET\x00")
        _proc(tmp_path, "103", b"usb://Brother/HL-1110\x00")  # no job argument
        _proc(tmp_path, "104", None)  # exited mid-scan
        (tmp_path / "self").mkdir()  # non-numeric entry
        monkeypatch.setattr(_stuck_job, "PROC_DIR", tmp_path)
        assert find_backend_pids() == {"105": 101}


class TestJobImpressions:
    @patch(f"{MOD}.shutil.which", return_value=None)
    def test_no_ipptool(self, w: MagicMock) -> None:
        assert _stuck_job._job_impressions("105") is None

    @patch(f"{MOD}.run_command_text")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/ipptool")
    def test_parses_counter(self, w: MagicMock, run: MagicMock) -> None:
        run.return_value = "        job-impressions-completed (integer) = 7\n"
        assert _stuck_job._job_impressions("105") == 7
        assert "ipp://localhost/jobs/105" in run.call_args.args[0]

    @patch(f"{MOD}.run_command_text", return_value="")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/ipptool")
    def test_counter_absent(self, w: MagicMock, r: MagicMock) -> None:
        assert _stuck_job._job_impressions("105") is None


class TestJobIsStalled:
    @patch(f"{MOD}._job_impressions", return_value=None)
    def test_unknown_counter_is_not_stalled(self, i: MagicMock) -> None:
        assert _stuck_job._job_is_stalled("105") is False

    @patch(f"{MOD}.time")
    @patch(f"{MOD}._job_impressions", side_effect=[7, 7, 8])
    def test_progress_clears_it(self, i: MagicMock, t: MagicMock) -> None:
        t.monotonic.side_effect = [0.0, 0.0, 1.0]
        assert _stuck_job._job_is_stalled("105") is False

    @patch(f"{MOD}.time")
    @patch(f"{MOD}._job_impressions", return_value=7)
    def test_frozen_counter_is_stalled(self, i: MagicMock, t: MagicMock) -> None:
        t.monotonic.side_effect = [0.0, 0.0, 10.0, 15.0]
        assert _stuck_job._job_is_stalled("105") is True
        assert t.sleep.call_count == 2


class TestDetectStuckJob:
    @patch(f"{MOD}._job_is_stalled")
    @patch(f"{MOD}.find_backend_pids", return_value={"104": 820758})
    def test_orphaned_backend(self, f: MagicMock, stalled: MagicMock) -> None:
        assert detect_stuck_job([]) == StuckJob("orphaned", "104", 820758)
        stalled.assert_not_called()

    @patch(f"{MOD}._job_is_stalled", return_value=True)
    @patch(f"{MOD}.find_backend_pids", return_value={"105": 884180})
    def test_stalled_job(self, f: MagicMock, s: MagicMock) -> None:
        assert detect_stuck_job(["105"]) == StuckJob("stalled", "105", 884180)

    @patch(f"{MOD}._job_is_stalled", return_value=True)
    @patch(f"{MOD}.find_backend_pids", return_value={})
    def test_stalled_before_backend_starts(self, f: MagicMock, s: MagicMock) -> None:
        assert detect_stuck_job(["105"]) == StuckJob("stalled", "105", 0)

    @patch(f"{MOD}._job_is_stalled", return_value=False)
    @patch(f"{MOD}.find_backend_pids", return_value={"105": 884180})
    def test_healthy_job(self, f: MagicMock, s: MagicMock) -> None:
        assert detect_stuck_job(["105"]) is None

    @patch(f"{MOD}.find_backend_pids", return_value={})
    def test_nothing_running(self, f: MagicMock) -> None:
        assert detect_stuck_job([]) is None


class TestKillBackend:
    @patch(f"{MOD}.os.kill")
    def test_sigkill(self, kill: MagicMock) -> None:
        assert kill_backend(42) is True
        kill.assert_called_once_with(42, _stuck_job.signal.SIGKILL)

    @patch(f"{MOD}.os.kill", side_effect=ProcessLookupError)
    def test_already_gone(self, k: MagicMock) -> None:
        assert kill_backend(42) is False


class TestOfferBackendKill:
    def _offer(self, answer: str, *, killed: bool = True) -> tuple[str, MagicMock]:
        with (
            patch(f"{MOD}._prompt", return_value=answer),
            patch(f"{MOD}.kill_backend", return_value=killed) as kill,
            patch("sys.stdout", new_callable=StringIO) as out,
        ):
            offer_backend_kill(42)
            return out.getvalue(), kill

    def test_declined(self) -> None:
        out, kill = self._offer("")
        kill.assert_not_called()
        assert "No changes made" in out

    def test_accepted(self) -> None:
        out, kill = self._offer(" Y ")
        kill.assert_called_once_with(42)
        assert "Backend killed" in out

    def test_kill_fails(self) -> None:
        out, _kill = self._offer("y", killed=False)
        assert "Could not kill PID 42" in out


class TestActiveJobIds:
    @patch(f"{MOD}.shutil.which", return_value=None)
    def test_no_lpstat(self, w: MagicMock) -> None:
        assert _stuck_job._active_job_ids("Brother") == []

    @patch(f"{MOD}.run_command_text")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lpstat")
    def test_parses_ids(self, w: MagicMock, run: MagicMock) -> None:
        run.return_value = (
            "Brother-105 kuhy 160768 Mon 12 Oct 2026\nOther-7 kuhy 1 Mon 12 Oct 2026\n"
        )
        assert _stuck_job._active_job_ids("Brother") == ["105"]


class TestFlagStuckJob:
    @patch(f"{MOD}._active_job_ids", return_value=[])
    @patch(f"{MOD}.detect_stuck_job", return_value=None)
    def test_nothing_stuck(self, d: MagicMock, a: MagicMock) -> None:
        result = USBResult(device="cups")
        assert flag_stuck_job(result, "Brother") is False
        assert result.status_code == ""

    @patch(f"{MOD}._active_job_ids", return_value=[])
    @patch(f"{MOD}.detect_stuck_job")
    def test_orphaned(self, detect: MagicMock, a: MagicMock) -> None:
        detect.return_value = StuckJob("orphaned", "104", 820758)
        result = USBResult(device="cups")
        assert flag_stuck_job(result, "Brother") is True
        assert result.status_code == DERIVED_BACKEND_ORPHANED
        assert result.cups.orphaned_backend_pid == 820758
        assert "cancelled job 104" in result.display

    @patch(f"{MOD}._active_job_ids", return_value=["105"])
    @patch(f"{MOD}.detect_stuck_job")
    def test_stalled(self, detect: MagicMock, a: MagicMock) -> None:
        detect.return_value = StuckJob("stalled", "105", 884180)
        result = USBResult(device="cups")
        assert flag_stuck_job(result, "Brother") is True
        assert result.status_code == DERIVED_JOB_STALLED
        assert result.cups.orphaned_backend_pid == 0
        assert "job 105" in result.display
