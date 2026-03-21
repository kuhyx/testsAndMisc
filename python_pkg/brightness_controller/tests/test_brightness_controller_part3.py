"""Tests for brightness_controller module - part 3 (toggle, daemon, auto)."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from python_pkg.brightness_controller import brightness_controller

if TYPE_CHECKING:
    from pathlib import Path

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


class TestToggleAuto:
    """Tests for _toggle_auto."""

    def test_toggles(self) -> None:
        ctrl = _make_controller()
        ctrl.auto_mode = False
        ctrl._set_auto = MagicMock()
        ctrl._toggle_auto()
        ctrl._set_auto.assert_called_once_with(enabled=True)


class TestReadDaemonState:
    """Tests for _read_daemon_state."""

    def test_enabled(self, tmp_path: Path) -> None:
        enabled_file = tmp_path / "enabled"
        enabled_file.write_text("1")
        with patch.object(brightness_controller, "ENABLED_FILE", enabled_file):
            assert (
                brightness_controller.BrightnessController._read_daemon_state() is True
            )

    def test_disabled(self, tmp_path: Path) -> None:
        enabled_file = tmp_path / "enabled"
        enabled_file.write_text("0")
        with patch.object(brightness_controller, "ENABLED_FILE", enabled_file):
            assert (
                brightness_controller.BrightnessController._read_daemon_state() is False
            )

    def test_missing_file(self, tmp_path: Path) -> None:
        enabled_file = tmp_path / "nonexistent"
        with patch.object(brightness_controller, "ENABLED_FILE", enabled_file):
            assert (
                brightness_controller.BrightnessController._read_daemon_state() is False
            )


class TestSetAuto:
    """Tests for _set_auto."""

    def test_enable(self, tmp_path: Path) -> None:
        config_dir = tmp_path / "config"
        enabled_file = config_dir / "enabled"
        ctrl = _make_controller()
        ctrl.als_path = tmp_path  # So _sync_auto_ui does something
        ctrl.auto_btn_var = MagicMock()
        ctrl.slider = MagicMock()
        with (
            patch.object(brightness_controller, "CONFIG_DIR", config_dir),
            patch.object(brightness_controller, "ENABLED_FILE", enabled_file),
        ):
            ctrl._set_auto(enabled=True)
        assert ctrl.auto_mode is True
        assert enabled_file.read_text() == "1"

    def test_disable(self, tmp_path: Path) -> None:
        config_dir = tmp_path / "config"
        enabled_file = config_dir / "enabled"
        ctrl = _make_controller()
        ctrl.als_path = tmp_path
        ctrl.auto_btn_var = MagicMock()
        ctrl.slider = MagicMock()
        with (
            patch.object(brightness_controller, "CONFIG_DIR", config_dir),
            patch.object(brightness_controller, "ENABLED_FILE", enabled_file),
        ):
            ctrl._set_auto(enabled=False)
        assert ctrl.auto_mode is False
        assert enabled_file.read_text() == "0"
