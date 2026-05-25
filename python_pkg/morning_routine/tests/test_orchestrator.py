"""Tests for the unified morning routine orchestrator."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from python_pkg.morning_routine._orchestrator import (
    ALARM_MODULE,
    WORKOUT_LOCK_MODULE,
    _parse_args,
    _run_alarm,
    _run_module,
    _run_workout_lock,
    main,
)

_ORCH = "python_pkg.morning_routine._orchestrator"


class TestRunModule:
    """Tests for _run_module."""

    def test_returns_subprocess_returncode(self) -> None:
        """Builds a `python -m <module> --production` command and returns rc."""
        proc = MagicMock(returncode=0)
        with patch(f"{_ORCH}.subprocess.run", return_value=proc) as mock_run:
            assert _run_module("some.module") == 0
        cmd = mock_run.call_args.args[0]
        assert cmd[1:] == ["-m", "some.module", "--production"]

    def test_nonzero_returncode_propagates(self) -> None:
        """A non-zero subprocess exit code is returned unchanged."""
        proc = MagicMock(returncode=3)
        with patch(f"{_ORCH}.subprocess.run", return_value=proc):
            assert _run_module("m") == 3

    def test_oserror_returns_one(self) -> None:
        """If the subprocess cannot start, return 1 instead of raising."""
        with patch(f"{_ORCH}.subprocess.run", side_effect=OSError("boom")):
            assert _run_module("m") == 1


class TestRunHelpers:
    """Tests for _run_alarm and _run_workout_lock."""

    def test_run_alarm_runs_alarm_module(self) -> None:
        """_run_alarm delegates to _run_module with the alarm module."""
        with patch(f"{_ORCH}._run_module", return_value=0) as mock_run:
            assert _run_alarm() == 0
        mock_run.assert_called_once_with(ALARM_MODULE)

    def test_run_workout_lock_runs_lock_module(self) -> None:
        """_run_workout_lock delegates to _run_module with the lock module."""
        with patch(f"{_ORCH}._run_module", return_value=0) as mock_run:
            assert _run_workout_lock() == 0
        mock_run.assert_called_once_with(WORKOUT_LOCK_MODULE)


class TestParseArgs:
    """Tests for _parse_args."""

    def test_with_alarm_flag(self) -> None:
        """--with-alarm sets with_alarm True."""
        assert _parse_args(["--with-alarm"]).with_alarm is True

    def test_default_no_alarm(self) -> None:
        """No flag leaves with_alarm False."""
        assert _parse_args([]).with_alarm is False

    def test_production_flag(self) -> None:
        """--production is accepted."""
        assert _parse_args(["--production"]).production is True


class TestMain:
    """Tests for main() sequencing."""

    def test_with_alarm_runs_alarm_then_lock(self) -> None:
        """--with-alarm runs the alarm first, then the workout lock, in order."""
        manager = MagicMock()
        with (
            patch(f"{_ORCH}._run_alarm", manager.alarm),
            patch(f"{_ORCH}._run_workout_lock", manager.lock),
            patch(f"{_ORCH}.sys") as mock_sys,
            patch(f"{_ORCH}.logging.basicConfig"),
        ):
            mock_sys.argv = ["orch", "--with-alarm"]
            main()
        assert [call[0] for call in manager.mock_calls] == ["alarm", "lock"]

    def test_without_alarm_runs_only_lock(self) -> None:
        """Without --with-alarm, the alarm is skipped and only the lock runs."""
        with (
            patch(f"{_ORCH}._run_alarm") as mock_alarm,
            patch(f"{_ORCH}._run_workout_lock") as mock_lock,
            patch(f"{_ORCH}.sys") as mock_sys,
            patch(f"{_ORCH}.logging.basicConfig"),
        ):
            mock_sys.argv = ["orch"]
            main()
        mock_alarm.assert_not_called()
        mock_lock.assert_called_once()
