"""Tests for brightness_controller module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from python_pkg.brightness_controller import brightness_controller

# ── _find_als_device ─────────────────────────────────────────────────────


class TestFindAlsDevice:
    """Tests for _find_als_device."""

    @patch.object(
        Path,
        "glob",
        return_value=[Path("/sys/bus/iio/devices/iio0/in_illuminance_raw")],
    )
    def test_found(self, _mock_glob: MagicMock) -> None:
        result = brightness_controller._find_als_device()
        assert result == Path("/sys/bus/iio/devices/iio0")

    @patch.object(Path, "glob", return_value=[])
    def test_not_found(self, _mock_glob: MagicMock) -> None:
        assert brightness_controller._find_als_device() is None


# ── _read_lux ────────────────────────────────────────────────────────────


class TestReadLux:
    """Tests for _read_lux."""

    def test_all_files_present(self, tmp_path: Path) -> None:
        (tmp_path / "in_illuminance_raw").write_text("100\n")
        (tmp_path / "in_illuminance_scale").write_text("2.0\n")
        (tmp_path / "in_illuminance_offset").write_text("5.0\n")
        assert brightness_controller._read_lux(tmp_path) == pytest.approx(210.0)

    def test_missing_scale(self, tmp_path: Path) -> None:
        (tmp_path / "in_illuminance_raw").write_text("50\n")
        (tmp_path / "in_illuminance_offset").write_text("0\n")
        assert brightness_controller._read_lux(tmp_path) == pytest.approx(50.0)

    def test_missing_offset(self, tmp_path: Path) -> None:
        (tmp_path / "in_illuminance_raw").write_text("50\n")
        (tmp_path / "in_illuminance_scale").write_text("1.0\n")
        assert brightness_controller._read_lux(tmp_path) == pytest.approx(50.0)

    def test_invalid_scale(self, tmp_path: Path) -> None:
        (tmp_path / "in_illuminance_raw").write_text("50\n")
        (tmp_path / "in_illuminance_scale").write_text("bad\n")
        (tmp_path / "in_illuminance_offset").write_text("0\n")
        assert brightness_controller._read_lux(tmp_path) == pytest.approx(50.0)

    def test_invalid_offset(self, tmp_path: Path) -> None:
        (tmp_path / "in_illuminance_raw").write_text("50\n")
        (tmp_path / "in_illuminance_scale").write_text("1.0\n")
        (tmp_path / "in_illuminance_offset").write_text("bad\n")
        assert brightness_controller._read_lux(tmp_path) == pytest.approx(50.0)


# ── _lux_to_brightness ──────────────────────────────────────────────────


class TestLuxToBrightness:
    """Tests for _lux_to_brightness."""

    def test_below_minimum(self) -> None:
        assert brightness_controller._lux_to_brightness(-1.0) == 10

    def test_at_minimum(self) -> None:
        assert brightness_controller._lux_to_brightness(0.0) == 10

    def test_above_maximum(self) -> None:
        assert brightness_controller._lux_to_brightness(10000.0) == 100

    def test_at_maximum(self) -> None:
        assert brightness_controller._lux_to_brightness(5000.0) == 100

    def test_interpolation(self) -> None:
        # Between (5.0, 40) and (50.0, 75), at lux=27.5
        assert brightness_controller._lux_to_brightness(27.5) == 57

    def test_fallback_return(self) -> None:
        """Exercise the post-loop fallback (unreachable with monotonic curves)."""
        nan = float("nan")
        with patch.object(
            brightness_controller,
            "LUX_CURVE",
            [(nan, 10), (nan, 99)],
        ):
            assert brightness_controller._lux_to_brightness(50.0) == 99


# ── _run_brightnessctl ───────────────────────────────────────────────────


class TestRunBrightnessctl:
    """Tests for _run_brightnessctl."""

    @patch("python_pkg.brightness_controller.brightness_controller.subprocess.run")
    def test_captures_stdout(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(stdout="  some output  ")
        result = brightness_controller._run_brightnessctl("-l", "-m")
        assert result == "some output"
        mock_run.assert_called_once_with(
            [brightness_controller._BRIGHTNESSCTL, "-l", "-m"],
            capture_output=True,
            text=True,
            check=False,
        )


# ── _get_devices ─────────────────────────────────────────────────────────


class TestGetDevices:
    """Tests for _get_devices."""

    @patch("python_pkg.brightness_controller.brightness_controller._run_brightnessctl")
    def test_returns_backlight_devices(self, mock_run: MagicMock) -> None:
        mock_run.return_value = (
            "intel_backlight,backlight,50,42%,120000\nkbd_backlight,leds,0,0%,3"
        )
        devices = brightness_controller._get_devices()
        assert len(devices) == 1
        assert devices[0].name == "intel_backlight"
        assert devices[0].device_class == "backlight"
        assert devices[0].current == 42
        assert devices[0].percent == "42%"
        assert devices[0].max_brightness == 120000

    @patch("python_pkg.brightness_controller.brightness_controller._run_brightnessctl")
    def test_empty_output(self, mock_run: MagicMock) -> None:
        mock_run.return_value = ""
        assert brightness_controller._get_devices() == []

    @patch("python_pkg.brightness_controller.brightness_controller._run_brightnessctl")
    def test_too_few_fields(self, mock_run: MagicMock) -> None:
        mock_run.return_value = "a,b,c"
        assert brightness_controller._get_devices() == []


# ── _get_brightness ──────────────────────────────────────────────────────


class TestGetBrightness:
    """Tests for _get_brightness."""

    @patch("python_pkg.brightness_controller.brightness_controller._run_brightnessctl")
    def test_valid(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = ["123", "intel_backlight,backlight,50,42%,120000"]
        assert brightness_controller._get_brightness("intel_backlight") == 42

    @patch("python_pkg.brightness_controller.brightness_controller._run_brightnessctl")
    def test_empty_get_output(self, mock_run: MagicMock) -> None:
        mock_run.return_value = ""
        assert brightness_controller._get_brightness("intel_backlight") == -1

    @patch("python_pkg.brightness_controller.brightness_controller._run_brightnessctl")
    def test_info_no_valid_fields(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = ["123", "a,b,c"]
        assert brightness_controller._get_brightness("intel_backlight") == -1


# ── _set_brightness ──────────────────────────────────────────────────────


class TestSetBrightness:
    """Tests for _set_brightness."""

    @patch("python_pkg.brightness_controller.brightness_controller._run_brightnessctl")
    def test_calls_brightnessctl(self, mock_run: MagicMock) -> None:
        brightness_controller._set_brightness("intel_backlight", 75)
        mock_run.assert_called_once_with("-d", "intel_backlight", "set", "75%")


# ── Device NamedTuple ────────────────────────────────────────────────────


class TestDevice:
    """Tests for Device NamedTuple."""

    def test_create(self) -> None:
        d = brightness_controller.Device("test", "backlight", 50, "50%", 1000)
        assert d.name == "test"
        assert d.max_brightness == 1000


# ── BrightnessController ────────────────────────────────────────────────


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
        patch(
            "python_pkg.brightness_controller.brightness_controller._get_devices",
            return_value=devices,
        ),
        patch(
            "python_pkg.brightness_controller.brightness_controller._find_als_device",
            return_value=als_path,
        ),
        patch.object(
            brightness_controller.BrightnessController,
            "_read_daemon_state",
            return_value=daemon_state,
        ),
        patch(
            "python_pkg.brightness_controller.brightness_controller.tk.Tk"
        ) as mock_tk,
        patch(
            "python_pkg.brightness_controller.brightness_controller.tk.StringVar"
        ) as mock_str_var,
        patch(
            "python_pkg.brightness_controller.brightness_controller.tk.IntVar"
        ) as mock_int_var,
        patch("python_pkg.brightness_controller.brightness_controller.ttk"),
        patch(
            "python_pkg.brightness_controller.brightness_controller._get_brightness",
            return_value=50,
        ),
    ):
        mock_root = MagicMock()
        mock_tk.return_value = mock_root
        mock_root.after = MagicMock()
        mock_str_var.return_value = MagicMock()
        mock_int_var.return_value = MagicMock()

        return brightness_controller.BrightnessController()


class TestBrightnessControllerInit:
    """Tests for BrightnessController.__init__."""

    def test_single_device(self) -> None:
        ctrl = _make_controller()
        assert ctrl.current_device == "intel_backlight"

    def test_no_devices(self) -> None:
        ctrl = _make_controller(devices=[])
        assert ctrl.current_device == ""

    def test_multiple_devices(self) -> None:
        devices = [
            brightness_controller.Device("led0", "leds", 0, "0%", 3),
            brightness_controller.Device("intel_bl", "backlight", 50, "50%", 120000),
        ]
        ctrl = _make_controller(devices=devices)
        # Should prefer backlight device
        assert ctrl.current_device == "intel_bl"

    def test_with_als(self, tmp_path: Path) -> None:
        ctrl = _make_controller(als_path=tmp_path)
        assert ctrl.als_path == tmp_path

    def test_auto_mode_enabled(self) -> None:
        ctrl = _make_controller(daemon_state=True)
        assert ctrl.auto_mode is True


class TestSelectDefaultDevice:
    """Tests for _select_default_device."""

    def test_no_devices_sets_message(self) -> None:
        ctrl = _make_controller(devices=[])
        ctrl.pct_var = MagicMock()
        ctrl._select_default_device()
        ctrl.pct_var.set.assert_called_with("No devices")

    def test_prefers_backlight(self) -> None:
        devices = [
            brightness_controller.Device("led0", "leds", 0, "0%", 3),
            brightness_controller.Device("bl", "backlight", 50, "50%", 120000),
        ]
        ctrl = _make_controller(devices=devices)
        ctrl._refresh_brightness = MagicMock()
        ctrl._select_default_device()
        assert ctrl.current_device == "bl"

    def test_no_backlight_device(self) -> None:
        """When no backlight device exists, uses the first device."""
        devices = [
            brightness_controller.Device("led0", "leds", 0, "0%", 3),
            brightness_controller.Device("led1", "leds", 0, "0%", 5),
        ]
        ctrl = _make_controller(devices=devices)
        ctrl._refresh_brightness = MagicMock()
        ctrl._select_default_device()
        assert ctrl.current_device == "led0"


class TestOnDeviceChange:
    """Tests for _on_device_change."""

    def test_updates_current_device(self) -> None:
        ctrl = _make_controller()
        ctrl.device_var = MagicMock()
        ctrl.device_var.get.return_value = "new_device"
        ctrl._refresh_brightness = MagicMock()
        ctrl._on_device_change(MagicMock())
        assert ctrl.current_device == "new_device"
        ctrl._refresh_brightness.assert_called_once()


class TestRefreshBrightness:
    """Tests for _refresh_brightness."""

    @patch(
        "python_pkg.brightness_controller.brightness_controller._get_brightness",
        return_value=75,
    )
    def test_updates_ui(self, _mock_get: MagicMock) -> None:
        ctrl = _make_controller()
        ctrl.pct_var = MagicMock()
        ctrl.slider_var = MagicMock()
        ctrl._refresh_brightness()
        ctrl.pct_var.set.assert_called_with("75%")
        ctrl.slider_var.set.assert_called_with(75)

    @patch(
        "python_pkg.brightness_controller.brightness_controller._get_brightness",
        return_value=-1,
    )
    def test_error(self, _mock_get: MagicMock) -> None:
        ctrl = _make_controller()
        ctrl.pct_var = MagicMock()
        ctrl._refresh_brightness()
        ctrl.pct_var.set.assert_called_with("Error")

    def test_no_current_device(self) -> None:
        ctrl = _make_controller(devices=[])
        ctrl.pct_var = MagicMock()
        ctrl._refresh_brightness()
        ctrl.pct_var.set.assert_not_called()


class TestOnSliderMove:
    """Tests for _on_slider_move."""

    @patch("python_pkg.brightness_controller.brightness_controller._set_brightness")
    def test_sets_brightness(self, mock_set: MagicMock) -> None:
        ctrl = _make_controller()
        ctrl.pct_var = MagicMock()
        ctrl._updating_slider = False
        ctrl._on_slider_move("75.0")
        mock_set.assert_called_once_with("intel_backlight", 75)
        ctrl.pct_var.set.assert_called_with("75%")

    def test_skips_during_update(self) -> None:
        ctrl = _make_controller()
        ctrl._updating_slider = True
        ctrl.pct_var = MagicMock()
        ctrl._on_slider_move("75.0")
        ctrl.pct_var.set.assert_not_called()

    def test_no_device(self) -> None:
        ctrl = _make_controller(devices=[])
        ctrl.pct_var = MagicMock()
        ctrl._on_slider_move("75.0")
        ctrl.pct_var.set.assert_not_called()

    @patch("python_pkg.brightness_controller.brightness_controller._set_brightness")
    def test_disables_auto_mode(self, _mock_set: MagicMock) -> None:
        ctrl = _make_controller(daemon_state=True)
        ctrl.auto_mode = True
        ctrl.pct_var = MagicMock()
        ctrl._set_auto = MagicMock()
        ctrl._updating_slider = False
        ctrl._on_slider_move("50.0")
        ctrl._set_auto.assert_called_once_with(enabled=False)


class TestSetPct:
    """Tests for _set_pct."""

    @patch("python_pkg.brightness_controller.brightness_controller._set_brightness")
    @patch(
        "python_pkg.brightness_controller.brightness_controller._get_brightness",
        return_value=25,
    )
    def test_sets_brightness(self, _mock_get: MagicMock, mock_set: MagicMock) -> None:
        ctrl = _make_controller()
        ctrl.pct_var = MagicMock()
        ctrl.slider_var = MagicMock()
        ctrl._set_pct(25)
        mock_set.assert_called_once_with("intel_backlight", 25)

    def test_no_device(self) -> None:
        ctrl = _make_controller(devices=[])
        # Should not raise
        ctrl._set_pct(50)


class TestDecrease:
    """Tests for _decrease."""

    @patch("python_pkg.brightness_controller.brightness_controller._set_brightness")
    @patch(
        "python_pkg.brightness_controller.brightness_controller._get_brightness",
        return_value=50,
    )
    def test_decrease(self, _mock_get: MagicMock, mock_set: MagicMock) -> None:
        ctrl = _make_controller()
        ctrl.pct_var = MagicMock()
        ctrl.slider_var = MagicMock()
        ctrl._decrease()
        mock_set.assert_called_once_with("intel_backlight", 45)

    @patch("python_pkg.brightness_controller.brightness_controller._set_brightness")
    @patch(
        "python_pkg.brightness_controller.brightness_controller._get_brightness",
        return_value=2,
    )
    def test_clamps_to_zero(self, _mock_get: MagicMock, mock_set: MagicMock) -> None:
        ctrl = _make_controller()
        ctrl.pct_var = MagicMock()
        ctrl.slider_var = MagicMock()
        ctrl._decrease()
        mock_set.assert_called_once_with("intel_backlight", 0)

    def test_no_device(self) -> None:
        ctrl = _make_controller(devices=[])
        ctrl._decrease()


class TestIncrease:
    """Tests for _increase."""

    @patch("python_pkg.brightness_controller.brightness_controller._set_brightness")
    @patch(
        "python_pkg.brightness_controller.brightness_controller._get_brightness",
        return_value=50,
    )
    def test_increase(self, _mock_get: MagicMock, mock_set: MagicMock) -> None:
        ctrl = _make_controller()
        ctrl.pct_var = MagicMock()
        ctrl.slider_var = MagicMock()
        ctrl._increase()
        mock_set.assert_called_once_with("intel_backlight", 55)

    @patch("python_pkg.brightness_controller.brightness_controller._set_brightness")
    @patch(
        "python_pkg.brightness_controller.brightness_controller._get_brightness",
        return_value=98,
    )
    def test_clamps_to_100(self, _mock_get: MagicMock, mock_set: MagicMock) -> None:
        ctrl = _make_controller()
        ctrl.pct_var = MagicMock()
        ctrl.slider_var = MagicMock()
        ctrl._increase()
        mock_set.assert_called_once_with("intel_backlight", 100)

    def test_no_device(self) -> None:
        ctrl = _make_controller(devices=[])
        ctrl._increase()
