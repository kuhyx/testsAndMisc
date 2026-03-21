"""Tests for auto_brightness_daemon module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from python_pkg.brightness_controller import auto_brightness_daemon

# ── _find_als_device ─────────────────────────────────────────────────────


class TestFindAlsDevice:
    """Tests for _find_als_device."""

    @patch.object(
        Path,
        "glob",
        return_value=[Path("/sys/bus/iio/devices/iio0/in_illuminance_raw")],
    )
    def test_found(self, _mock_glob: MagicMock) -> None:
        result = auto_brightness_daemon._find_als_device()
        assert result == Path("/sys/bus/iio/devices/iio0")

    @patch.object(Path, "glob", return_value=[])
    def test_not_found(self, _mock_glob: MagicMock) -> None:
        assert auto_brightness_daemon._find_als_device() is None


# ── _read_lux ────────────────────────────────────────────────────────────


class TestReadLux:
    """Tests for _read_lux."""

    def test_basic_read(self, tmp_path: Path) -> None:
        (tmp_path / "in_illuminance_raw").write_text("100\n")
        (tmp_path / "in_illuminance_scale").write_text("2.0\n")
        (tmp_path / "in_illuminance_offset").write_text("5.0\n")
        result = auto_brightness_daemon._read_lux(tmp_path)
        assert result == pytest.approx((100 + 5.0) * 2.0)

    def test_missing_scale(self, tmp_path: Path) -> None:
        (tmp_path / "in_illuminance_raw").write_text("50\n")
        # No scale file → default 1.0
        (tmp_path / "in_illuminance_offset").write_text("0\n")
        result = auto_brightness_daemon._read_lux(tmp_path)
        assert result == pytest.approx(50.0)

    def test_missing_offset(self, tmp_path: Path) -> None:
        (tmp_path / "in_illuminance_raw").write_text("50\n")
        (tmp_path / "in_illuminance_scale").write_text("1.0\n")
        # No offset file → default 0.0
        result = auto_brightness_daemon._read_lux(tmp_path)
        assert result == pytest.approx(50.0)

    def test_invalid_scale_value(self, tmp_path: Path) -> None:
        (tmp_path / "in_illuminance_raw").write_text("50\n")
        (tmp_path / "in_illuminance_scale").write_text("bad\n")
        (tmp_path / "in_illuminance_offset").write_text("0\n")
        result = auto_brightness_daemon._read_lux(tmp_path)
        assert result == pytest.approx(50.0)

    def test_invalid_offset_value(self, tmp_path: Path) -> None:
        (tmp_path / "in_illuminance_raw").write_text("50\n")
        (tmp_path / "in_illuminance_scale").write_text("1.0\n")
        (tmp_path / "in_illuminance_offset").write_text("bad\n")
        result = auto_brightness_daemon._read_lux(tmp_path)
        assert result == pytest.approx(50.0)


# ── _lux_to_brightness ──────────────────────────────────────────────────


class TestLuxToBrightness:
    """Tests for _lux_to_brightness."""

    def test_below_minimum(self) -> None:
        assert auto_brightness_daemon._lux_to_brightness(-10.0) == 10

    def test_at_minimum(self) -> None:
        assert auto_brightness_daemon._lux_to_brightness(0.0) == 10

    def test_above_maximum(self) -> None:
        assert auto_brightness_daemon._lux_to_brightness(10000.0) == 100

    def test_at_maximum(self) -> None:
        assert auto_brightness_daemon._lux_to_brightness(5000.0) == 100

    def test_interpolation_mid(self) -> None:
        result = auto_brightness_daemon._lux_to_brightness(27.5)
        assert result == 57

    def test_interpolation_first_segment(self) -> None:
        result = auto_brightness_daemon._lux_to_brightness(2.5)
        assert result == 25

    def test_fallback_return(self) -> None:
        """Exercise the post-loop fallback (unreachable with monotonic curves)."""
        nan = float("nan")
        with patch.object(
            auto_brightness_daemon,
            "LUX_CURVE",
            [(nan, 10), (nan, 99)],
        ):
            assert auto_brightness_daemon._lux_to_brightness(50.0) == 99


# ── _get_brightness ──────────────────────────────────────────────────────


class TestGetBrightness:
    """Tests for _get_brightness."""

    @patch("python_pkg.brightness_controller.auto_brightness_daemon.subprocess.run")
    def test_valid_output(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            stdout="intel_backlight,backlight,50,42%,120000"
        )
        assert auto_brightness_daemon._get_brightness() == 42

    @patch("python_pkg.brightness_controller.auto_brightness_daemon.subprocess.run")
    def test_no_backlight_device(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(stdout="kbd_backlight,leds,0,0%,3")
        assert auto_brightness_daemon._get_brightness() == -1

    @patch("python_pkg.brightness_controller.auto_brightness_daemon.subprocess.run")
    def test_too_few_fields(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(stdout="a,b,c")
        assert auto_brightness_daemon._get_brightness() == -1

    @patch("python_pkg.brightness_controller.auto_brightness_daemon.subprocess.run")
    def test_empty_output(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(stdout="")
        assert auto_brightness_daemon._get_brightness() == -1


# ── _set_brightness ──────────────────────────────────────────────────────


class TestSetBrightness:
    """Tests for _set_brightness."""

    @patch("python_pkg.brightness_controller.auto_brightness_daemon.subprocess.run")
    def test_calls_brightnessctl(self, mock_run: MagicMock) -> None:
        auto_brightness_daemon._set_brightness(75)
        mock_run.assert_called_once_with(
            [auto_brightness_daemon._BRIGHTNESSCTL, "-q", "set", "75%"],
            check=False,
        )


# ── _is_enabled ──────────────────────────────────────────────────────────


class TestIsEnabled:
    """Tests for _is_enabled."""

    def test_enabled(self, tmp_path: Path) -> None:
        enabled_file = tmp_path / "enabled"
        enabled_file.write_text("1\n")
        with patch.object(auto_brightness_daemon, "ENABLED_FILE", enabled_file):
            assert auto_brightness_daemon._is_enabled() is True

    def test_disabled(self, tmp_path: Path) -> None:
        enabled_file = tmp_path / "enabled"
        enabled_file.write_text("0\n")
        with patch.object(auto_brightness_daemon, "ENABLED_FILE", enabled_file):
            assert auto_brightness_daemon._is_enabled() is False

    def test_missing_file(self, tmp_path: Path) -> None:
        enabled_file = tmp_path / "nonexistent"
        with patch.object(auto_brightness_daemon, "ENABLED_FILE", enabled_file):
            assert auto_brightness_daemon._is_enabled() is False


# ── _set_enabled ─────────────────────────────────────────────────────────


class TestSetEnabled:
    """Tests for _set_enabled."""

    def test_enable(self, tmp_path: Path) -> None:
        config_dir = tmp_path / "config"
        enabled_file = config_dir / "enabled"
        with (
            patch.object(auto_brightness_daemon, "CONFIG_DIR", config_dir),
            patch.object(auto_brightness_daemon, "ENABLED_FILE", enabled_file),
        ):
            auto_brightness_daemon._set_enabled(enabled=True)
            assert enabled_file.read_text() == "1"

    def test_disable(self, tmp_path: Path) -> None:
        config_dir = tmp_path / "config"
        enabled_file = config_dir / "enabled"
        with (
            patch.object(auto_brightness_daemon, "CONFIG_DIR", config_dir),
            patch.object(auto_brightness_daemon, "ENABLED_FILE", enabled_file),
        ):
            auto_brightness_daemon._set_enabled(enabled=False)
            assert enabled_file.read_text() == "0"


# ── _clamp ───────────────────────────────────────────────────────────────


class TestClamp:
    """Tests for _clamp."""

    def test_within_range(self) -> None:
        assert auto_brightness_daemon._clamp(5, 0, 10) == 5

    def test_below_low(self) -> None:
        assert auto_brightness_daemon._clamp(-5, 0, 10) == 0

    def test_above_high(self) -> None:
        assert auto_brightness_daemon._clamp(15, 0, 10) == 10


# ── main ─────────────────────────────────────────────────────────────────
