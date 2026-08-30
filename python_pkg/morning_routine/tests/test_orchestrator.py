"""Tests for the unified morning routine orchestrator."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from python_pkg.morning_routine._orchestrator import (
    WORKOUT_LOCK_MODULE,
    _parse_args,
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
    """Tests for _run_workout_lock."""

    def test_run_workout_lock_runs_lock_module(self) -> None:
        """_run_workout_lock delegates to _run_module with the lock module."""
        with patch(f"{_ORCH}._run_module", return_value=0) as mock_run:
            assert _run_workout_lock() == 0
        mock_run.assert_called_once_with(WORKOUT_LOCK_MODULE)


class TestParseArgs:
    """Tests for _parse_args."""

    def test_production_flag(self) -> None:
        """--production is accepted."""
        assert _parse_args(["--production"]).production is True


class TestMain:
    """Tests for main()."""

    def test_main_runs_the_workout_lock(self) -> None:
        """The one remaining leg runs; the alarm leg is gone entirely."""
        with (
            patch(f"{_ORCH}._run_workout_lock") as mock_lock,
            patch(f"{_ORCH}.sys") as mock_sys,
            patch(f"{_ORCH}.logging.basicConfig"),
        ):
            mock_sys.argv = ["orch"]
            main()
        mock_lock.assert_called_once()

    def test_production_flag_is_still_accepted(self) -> None:
        """systemd passes --production; main must not choke on it."""
        with (
            patch(f"{_ORCH}._run_workout_lock") as mock_lock,
            patch(f"{_ORCH}.sys") as mock_sys,
            patch(f"{_ORCH}.logging.basicConfig"),
        ):
            mock_sys.argv = ["orch", "--production"]
            main()
        mock_lock.assert_called_once()
