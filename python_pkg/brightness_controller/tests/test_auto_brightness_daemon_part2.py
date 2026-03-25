"""Tests for auto_brightness_daemon module - part 2 (main function)."""

from __future__ import annotations

import contextlib
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from python_pkg.brightness_controller import auto_brightness_daemon

MOD = "python_pkg.brightness_controller.auto_brightness_daemon"


class TestMainNoAls:
    """Tests for main() when no ALS device is found."""

    @patch(f"{MOD}._find_als_device", return_value=None)
    def test_exits_when_no_als(self, mock_find: MagicMock) -> None:
        with pytest.raises(SystemExit, match="1"):
            auto_brightness_daemon.main()


class TestMainDaemonLoop:
    """Tests for main() daemon loop behaviour."""

    def _run_main_with_iterations(
        self,
        *,
        enabled: bool = True,
        lux: float = 50.0,
        current_brightness: int = 50,
        enabled_file_exists: bool = True,
        signal_after: int = 1,
    ) -> tuple[MagicMock, MagicMock]:
        """Helper to run main() with controlled loop iterations.

        Returns (mock_set_brightness, mock_read_lux).
        """
        als_path = Path("/fake/als")
        iteration = 0

        def fake_sleep(_t: float) -> None:
            nonlocal iteration
            iteration += 1
            if iteration >= signal_after:
                raise KeyboardInterrupt

        mock_set_brightness = MagicMock()
        mock_enabled_file = MagicMock()
        mock_enabled_file.exists.return_value = enabled_file_exists

        with (
            patch(f"{MOD}._find_als_device", return_value=als_path),
            patch(f"{MOD}.ENABLED_FILE", mock_enabled_file),
            patch(f"{MOD}._set_enabled"),
            patch(f"{MOD}.signal.signal"),
            patch(f"{MOD}.time.sleep", side_effect=fake_sleep),
            patch(f"{MOD}._is_enabled", return_value=enabled),
            patch(f"{MOD}._read_lux", return_value=lux) as mock_lux,
            patch(f"{MOD}._lux_to_brightness", return_value=75),
            patch(f"{MOD}._get_brightness", return_value=current_brightness),
            patch(f"{MOD}._set_brightness", mock_set_brightness),
            contextlib.suppress(KeyboardInterrupt),
        ):
            # Simulate SIGINT by raising KeyboardInterrupt in sleep
            auto_brightness_daemon.main()

        return mock_set_brightness, mock_lux

    def test_adjusts_brightness_when_delta_exceeds_threshold(self) -> None:
        mock_set, _ = self._run_main_with_iterations(
            enabled=True,
            current_brightness=50,
        )
        # target=75, current=50, delta=25, step clamped to MAX_STEP_PER_TICK=5
        mock_set.assert_called_with(55)

    def test_skips_when_disabled(self) -> None:
        mock_set, _ = self._run_main_with_iterations(enabled=False)
        mock_set.assert_not_called()

    def test_skips_when_delta_too_small(self) -> None:
        # target=75, current=74 → delta=1 < MIN_CHANGE_PERCENT=2
        with (
            patch(f"{MOD}._find_als_device", return_value=Path("/fake")),
            patch(
                f"{MOD}.ENABLED_FILE", MagicMock(exists=MagicMock(return_value=True))
            ),
            patch(f"{MOD}._set_enabled"),
            patch(f"{MOD}.signal.signal"),
            patch(f"{MOD}.time.sleep", side_effect=[None, KeyboardInterrupt]),
            patch(f"{MOD}._is_enabled", return_value=True),
            patch(f"{MOD}._read_lux", return_value=50.0),
            patch(f"{MOD}._lux_to_brightness", return_value=74),
            patch(f"{MOD}._get_brightness", return_value=74),
            patch(f"{MOD}._set_brightness") as mock_set,
            contextlib.suppress(KeyboardInterrupt),
        ):
            auto_brightness_daemon.main()
        mock_set.assert_not_called()

    def test_skips_when_brightness_negative(self) -> None:
        # current=-1 means error → should not set brightness
        with (
            patch(f"{MOD}._find_als_device", return_value=Path("/fake")),
            patch(
                f"{MOD}.ENABLED_FILE", MagicMock(exists=MagicMock(return_value=True))
            ),
            patch(f"{MOD}._set_enabled"),
            patch(f"{MOD}.signal.signal"),
            patch(f"{MOD}.time.sleep", side_effect=[None, KeyboardInterrupt]),
            patch(f"{MOD}._is_enabled", return_value=True),
            patch(f"{MOD}._read_lux", return_value=50.0),
            patch(f"{MOD}._lux_to_brightness", return_value=75),
            patch(f"{MOD}._get_brightness", return_value=-1),
            patch(f"{MOD}._set_brightness") as mock_set,
            contextlib.suppress(KeyboardInterrupt),
        ):
            auto_brightness_daemon.main()
        mock_set.assert_not_called()

    def test_creates_control_file_when_missing(self) -> None:
        mock_set_enabled = MagicMock()
        mock_enabled_file = MagicMock()
        mock_enabled_file.exists.return_value = False

        with (
            patch(f"{MOD}._find_als_device", return_value=Path("/fake")),
            patch(f"{MOD}.ENABLED_FILE", mock_enabled_file),
            patch(f"{MOD}._set_enabled", mock_set_enabled),
            patch(f"{MOD}.signal.signal"),
            patch(f"{MOD}.time.sleep", side_effect=KeyboardInterrupt),
            patch(f"{MOD}._is_enabled", return_value=False),
            contextlib.suppress(KeyboardInterrupt),
        ):
            auto_brightness_daemon.main()
        mock_set_enabled.assert_called_once_with(enabled=True)

    def test_does_not_create_file_when_exists(self) -> None:
        mock_set_enabled = MagicMock()
        mock_enabled_file = MagicMock()
        mock_enabled_file.exists.return_value = True

        with (
            patch(f"{MOD}._find_als_device", return_value=Path("/fake")),
            patch(f"{MOD}.ENABLED_FILE", mock_enabled_file),
            patch(f"{MOD}._set_enabled", mock_set_enabled),
            patch(f"{MOD}.signal.signal"),
            patch(f"{MOD}.time.sleep", side_effect=KeyboardInterrupt),
            patch(f"{MOD}._is_enabled", return_value=False),
            contextlib.suppress(KeyboardInterrupt),
        ):
            auto_brightness_daemon.main()
        mock_set_enabled.assert_not_called()

    def test_handles_exception_in_loop_gracefully(self) -> None:
        """Exception in the loop body is caught and logged."""
        with (
            patch(f"{MOD}._find_als_device", return_value=Path("/fake")),
            patch(
                f"{MOD}.ENABLED_FILE", MagicMock(exists=MagicMock(return_value=True))
            ),
            patch(f"{MOD}._set_enabled"),
            patch(f"{MOD}.signal.signal"),
            patch(f"{MOD}.time.sleep", side_effect=[None, KeyboardInterrupt]),
            patch(f"{MOD}._is_enabled", side_effect=OSError("disk fail")),
            contextlib.suppress(KeyboardInterrupt),
        ):
            auto_brightness_daemon.main()
            # No crash = exception was handled

    def test_signal_handler_stops_loop(self) -> None:
        """SIGTERM handler sets running=False to stop the loop."""
        captured_handler = {}

        def capture_signal(signum: int, handler: object) -> None:
            captured_handler[signum] = handler

        import signal

        with (
            patch(f"{MOD}._find_als_device", return_value=Path("/fake")),
            patch(
                f"{MOD}.ENABLED_FILE", MagicMock(exists=MagicMock(return_value=True))
            ),
            patch(f"{MOD}._set_enabled"),
            patch(f"{MOD}.signal.signal", side_effect=capture_signal),
            patch(f"{MOD}.time.sleep", side_effect=KeyboardInterrupt),
            patch(f"{MOD}._is_enabled", return_value=False),
            contextlib.suppress(KeyboardInterrupt),
        ):
            auto_brightness_daemon.main()

        # Verify we captured a SIGTERM handler
        assert signal.SIGTERM in captured_handler
        # Call the handler to verify it doesn't crash
        handler = captured_handler[signal.SIGTERM]
        assert callable(handler)
        handler(signal.SIGTERM, None)

    def test_negative_delta_clamps_step_down(self) -> None:
        """When target < current, step is negative and clamped."""
        # target=75 is set by _lux_to_brightness mock
        # current=90 → delta=-15, step clamped to -MAX_STEP_PER_TICK=-5
        with (
            patch(f"{MOD}._find_als_device", return_value=Path("/fake")),
            patch(
                f"{MOD}.ENABLED_FILE", MagicMock(exists=MagicMock(return_value=True))
            ),
            patch(f"{MOD}._set_enabled"),
            patch(f"{MOD}.signal.signal"),
            patch(f"{MOD}.time.sleep", side_effect=[None, KeyboardInterrupt]),
            patch(f"{MOD}._is_enabled", return_value=True),
            patch(f"{MOD}._read_lux", return_value=0.0),
            patch(f"{MOD}._lux_to_brightness", return_value=10),
            patch(f"{MOD}._get_brightness", return_value=90),
            patch(f"{MOD}._set_brightness") as mock_set,
            contextlib.suppress(KeyboardInterrupt),
        ):
            auto_brightness_daemon.main()
        # delta=-80, step=-5, new_val=85
        mock_set.assert_called_with(85)

    def test_graceful_shutdown_via_signal(self) -> None:
        """When signal handler sets running=False, loop exits normally."""
        captured_handler: dict[int, object] = {}

        def capture_signal(signum: int, handler: object) -> None:
            captured_handler[signum] = handler

        import signal as sig_mod

        def fake_sleep(_t: float) -> None:
            # Call the SIGTERM handler on first sleep to stop the loop
            handler = captured_handler.get(sig_mod.SIGTERM)
            if callable(handler):
                handler(sig_mod.SIGTERM, None)

        with (
            patch(f"{MOD}._find_als_device", return_value=Path("/fake")),
            patch(
                f"{MOD}.ENABLED_FILE", MagicMock(exists=MagicMock(return_value=True))
            ),
            patch(f"{MOD}._set_enabled"),
            patch(f"{MOD}.signal.signal", side_effect=capture_signal),
            patch(f"{MOD}.time.sleep", side_effect=fake_sleep),
            patch(f"{MOD}._is_enabled", return_value=False),
        ):
            auto_brightness_daemon.main()
