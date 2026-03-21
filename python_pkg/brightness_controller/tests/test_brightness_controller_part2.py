"""Tests for brightness_controller module - part 2 (poll + main)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from python_pkg.brightness_controller import brightness_controller

MOD = "python_pkg.brightness_controller.brightness_controller"


def _make_controller(
    devices: list[brightness_controller.Device] | None = None,
    als_path: Path | None = None,
    *,
    daemon_state: bool = False,
) -> brightness_controller.BrightnessController:
    """Create a BrightnessController with all Tk operations mocked."""
    if devices is None:
        devices = [
            brightness_controller.Device(
                "intel_backlight", "backlight", 50, "50%", 120000
            )
        ]

    with (
        patch(f"{MOD}._get_devices", return_value=devices),
        patch(f"{MOD}._find_als_device", return_value=als_path),
        patch.object(
            brightness_controller.BrightnessController,
            "_read_daemon_state",
            return_value=daemon_state,
        ),
        patch(f"{MOD}.tk.Tk") as mock_tk,
        patch(f"{MOD}.tk.StringVar") as mock_str_var,
        patch(f"{MOD}.tk.IntVar") as mock_int_var,
        patch(f"{MOD}.ttk"),
        patch(f"{MOD}._get_brightness", return_value=50),
    ):
        mock_root = MagicMock()
        mock_tk.return_value = mock_root
        mock_root.after = MagicMock()
        mock_str_var.return_value = MagicMock()
        mock_int_var.return_value = MagicMock()

        return brightness_controller.BrightnessController()


# ── _sync_auto_ui ────────────────────────────────────────────────────


class TestSyncAutoUi:
    """Tests for _sync_auto_ui."""

    def test_no_als_returns_early(self) -> None:
        ctrl = _make_controller(als_path=None)
        ctrl.als_path = None
        ctrl.auto_btn_var = MagicMock()
        ctrl.slider = MagicMock()
        ctrl._sync_auto_ui()
        ctrl.auto_btn_var.set.assert_not_called()

    def test_auto_on(self) -> None:
        ctrl = _make_controller(als_path=Path("/fake"))
        ctrl.auto_mode = True
        ctrl.auto_btn_var = MagicMock()
        ctrl.slider = MagicMock()
        ctrl._sync_auto_ui()
        ctrl.auto_btn_var.set.assert_called_once()
        assert "ON" in ctrl.auto_btn_var.set.call_args[0][0]
        ctrl.slider.state.assert_called_once_with(["disabled"])

    def test_auto_off(self) -> None:
        ctrl = _make_controller(als_path=Path("/fake"))
        ctrl.auto_mode = False
        ctrl.auto_btn_var = MagicMock()
        ctrl.slider = MagicMock()
        ctrl._sync_auto_ui()
        ctrl.auto_btn_var.set.assert_called_once()
        assert "OFF" in ctrl.auto_btn_var.set.call_args[0][0]
        ctrl.slider.state.assert_called_once_with(["!disabled"])


# ── _poll_als ────────────────────────────────────────────────────────


class TestPollAls:
    """Tests for _poll_als."""

    @patch(f"{MOD}._read_lux", return_value=42.5)
    def test_updates_lux_display(self, _mock_lux: MagicMock) -> None:
        ctrl = _make_controller(als_path=Path("/fake"))
        ctrl.lux_var = MagicMock()
        ctrl.root = MagicMock()
        with patch.object(
            brightness_controller.BrightnessController,
            "_read_daemon_state",
            return_value=False,
        ):
            ctrl._poll_als()
        assert "42.5 lux" in ctrl.lux_var.set.call_args[0][0]
        ctrl.root.after.assert_called_once()

    @patch(f"{MOD}._read_lux", side_effect=OSError("sensor fail"))
    def test_sensor_error(self, _mock_lux: MagicMock) -> None:
        ctrl = _make_controller(als_path=Path("/fake"))
        ctrl.lux_var = MagicMock()
        ctrl.root = MagicMock()
        with patch.object(
            brightness_controller.BrightnessController,
            "_read_daemon_state",
            return_value=False,
        ):
            ctrl._poll_als()
        ctrl.lux_var.set.assert_called_with("sensor error")

    @patch(f"{MOD}._read_lux", side_effect=ValueError("bad value"))
    def test_sensor_value_error(self, _mock_lux: MagicMock) -> None:
        ctrl = _make_controller(als_path=Path("/fake"))
        ctrl.lux_var = MagicMock()
        ctrl.root = MagicMock()
        with patch.object(
            brightness_controller.BrightnessController,
            "_read_daemon_state",
            return_value=False,
        ):
            ctrl._poll_als()
        ctrl.lux_var.set.assert_called_with("sensor error")

    @patch(f"{MOD}._read_lux", return_value=10.0)
    def test_syncs_daemon_state_change(self, _mock_lux: MagicMock) -> None:
        """When daemon state differs from auto_mode, syncs it."""
        ctrl = _make_controller(als_path=Path("/fake"))
        ctrl.auto_mode = False
        ctrl.lux_var = MagicMock()
        ctrl.auto_btn_var = MagicMock()
        ctrl.slider = MagicMock()
        ctrl.root = MagicMock()
        with patch.object(
            brightness_controller.BrightnessController,
            "_read_daemon_state",
            return_value=True,
        ):
            ctrl._poll_als()
        assert ctrl.auto_mode is True

    @patch(f"{MOD}._read_lux", return_value=10.0)
    def test_no_sync_when_same(self, _mock_lux: MagicMock) -> None:
        """When daemon state matches auto_mode, no sync needed."""
        ctrl = _make_controller(als_path=Path("/fake"))
        ctrl.auto_mode = False
        ctrl.lux_var = MagicMock()
        ctrl.root = MagicMock()
        with patch.object(
            brightness_controller.BrightnessController,
            "_read_daemon_state",
            return_value=False,
        ):
            ctrl._poll_als()
        # No assertion on auto_btn_var since auto_mode didn't change

    def test_no_als_path(self) -> None:
        ctrl = _make_controller(als_path=None)
        ctrl.als_path = None
        ctrl.root = MagicMock()
        ctrl._poll_als()
        ctrl.root.after.assert_called_once()


# ── _poll_brightness ─────────────────────────────────────────────────


class TestPollBrightness:
    """Tests for _poll_brightness."""

    @patch(f"{MOD}._get_brightness", return_value=60)
    def test_refreshes_when_not_auto(self, _mock_get: MagicMock) -> None:
        ctrl = _make_controller()
        ctrl.auto_mode = False
        ctrl.pct_var = MagicMock()
        ctrl.slider_var = MagicMock()
        ctrl.root = MagicMock()
        ctrl._poll_brightness()
        ctrl.pct_var.set.assert_called_with("60%")
        ctrl.root.after.assert_called_once()

    def test_skips_refresh_when_auto(self) -> None:
        ctrl = _make_controller()
        ctrl.auto_mode = True
        ctrl._refresh_brightness = MagicMock()
        ctrl.root = MagicMock()
        ctrl._poll_brightness()
        ctrl._refresh_brightness.assert_not_called()
        ctrl.root.after.assert_called_once()


# ── run ──────────────────────────────────────────────────────────────


class TestRun:
    """Tests for run method."""

    def test_calls_mainloop(self) -> None:
        ctrl = _make_controller()
        ctrl.root = MagicMock()
        ctrl.run()
        ctrl.root.mainloop.assert_called_once()


# ── main ─────────────────────────────────────────────────────────────


class TestMain:
    """Tests for main() entry point."""

    @patch(f"{MOD}.subprocess.run")
    def test_brightnessctl_not_found(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = FileNotFoundError
        with pytest.raises(SystemExit, match="1"):
            brightness_controller.main()

    @patch(f"{MOD}.BrightnessController")
    @patch(f"{MOD}.subprocess.run")
    def test_success(self, mock_run: MagicMock, mock_ctrl_cls: MagicMock) -> None:
        mock_run.return_value = MagicMock()
        mock_app = MagicMock()
        mock_ctrl_cls.return_value = mock_app
        brightness_controller.main()
        mock_app.run.assert_called_once()
