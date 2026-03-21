"""Tests for brother_printer.cups_service module - part 2."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

from python_pkg.brother_printer.cups_service import (
    _cups_reasons_to_error,
    _get_cups_economode,
    _get_printer_info_from_cups,
    _map_cups_to_status_code,
    _parse_cups_usb_uri,
    _port_status_to_status_code,
    find_cups_printer_name,
)
from python_pkg.brother_printer.data_classes import (
    USBPortStatus,
)

MOD = "python_pkg.brother_printer.cups_service"


# ── _get_cups_economode ──────────────────────────────────────────────


class TestGetCupsEconomode:
    """Tests for _get_cups_economode."""

    @patch(f"{MOD}.shutil.which", return_value=None)
    def test_no_lpoptions(self, _m: MagicMock) -> None:
        assert _get_cups_economode("Brother") == ""

    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lpoptions")
    def test_economode_on(self, _w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            stdout="BREconomode/Toner Save Mode: *True False\n"
        )
        assert _get_cups_economode("Brother") == "ON"

    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lpoptions")
    def test_economode_off(self, _w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            stdout="BREconomode/Toner Save Mode: True *False\n"
        )
        assert _get_cups_economode("Brother") == "OFF"

    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lpoptions")
    def test_no_economode_line(self, _w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            stdout="Resolution/Output Resolution: 600dpi *1200dpi\n"
        )
        assert _get_cups_economode("Brother") == ""

    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lpoptions")
    def test_economode_no_star_match(self, _w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            stdout="BREconomode/Toner Save Mode: True False\n"
        )
        assert _get_cups_economode("Brother") == ""

    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lpoptions")
    def test_timeout(self, _w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired("lpoptions", 5)
        assert _get_cups_economode("Brother") == ""

    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lpoptions")
    def test_oserror(self, _w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.side_effect = OSError("fail")
        assert _get_cups_economode("Brother") == ""


# ── _map_cups_to_status_code ─────────────────────────────────────────


class TestMapCupsToStatusCode:
    """Tests for _map_cups_to_status_code."""

    def test_reason_match(self) -> None:
        result = _map_cups_to_status_code("idle", "toner-low-report")
        assert result == "30010"

    def test_state_match(self) -> None:
        result = _map_cups_to_status_code("idle", "none")
        assert result == "10001"

    def test_processing_state(self) -> None:
        result = _map_cups_to_status_code("processing", "none")
        assert result == "10007"

    def test_stopped_state(self) -> None:
        result = _map_cups_to_status_code("stopped", "none")
        assert result == "10023"

    def test_unknown_state(self) -> None:
        result = _map_cups_to_status_code("mystery", "none")
        assert result == "10001"

    def test_state_with_parenthetical(self) -> None:
        result = _map_cups_to_status_code("idle (on fire)", "none")
        assert result == "10001"


# ── _cups_reasons_to_error ───────────────────────────────────────────


class TestCupsReasonsToError:
    """Tests for _cups_reasons_to_error."""

    def test_media_jam(self) -> None:
        code, display = _cups_reasons_to_error("media-jam-report")
        assert code == "40000"
        assert display == "Paper Jam"

    def test_cover_open(self) -> None:
        code, display = _cups_reasons_to_error("cover-open")
        assert code == "41000"

    def test_door_open(self) -> None:
        code, display = _cups_reasons_to_error("door-open")
        assert code == "41000"

    def test_toner_empty(self) -> None:
        code, display = _cups_reasons_to_error("toner-empty")
        assert code == "40310"

    def test_toner_low(self) -> None:
        code, display = _cups_reasons_to_error("toner-low")
        assert code == "30010"

    def test_unknown_reason(self) -> None:
        code, display = _cups_reasons_to_error("something-weird")
        assert code == "42000"
        assert display == "Printer Error"


# ── _port_status_to_status_code ──────────────────────────────────────


class TestPortStatusToStatusCode:
    """Tests for _port_status_to_status_code."""

    def test_error_and_paper_empty(self) -> None:
        ps = USBPortStatus(error=True, paper_empty=True, online=True)
        code, display = _port_status_to_status_code(ps, "none")
        assert code == "40302"
        assert display == "No Paper"

    def test_error_and_not_online(self) -> None:
        ps = USBPortStatus(error=True, paper_empty=False, online=False)
        code, display = _port_status_to_status_code(ps, "none")
        assert code == "41000"
        assert display == "Cover Open"

    def test_error_only(self) -> None:
        ps = USBPortStatus(error=True, paper_empty=False, online=True)
        code, display = _port_status_to_status_code(ps, "media-jam")
        assert code == "40000"

    def test_paper_empty_no_error(self) -> None:
        ps = USBPortStatus(error=False, paper_empty=True, online=True)
        code, display = _port_status_to_status_code(ps, "none")
        assert code == "40302"

    def test_not_online_no_error(self) -> None:
        ps = USBPortStatus(error=False, paper_empty=False, online=False)
        code, display = _port_status_to_status_code(ps, "none")
        assert code == "10002"
        assert display == "Offline / Sleep"

    def test_all_ok(self) -> None:
        ps = USBPortStatus(error=False, paper_empty=False, online=True)
        code, display = _port_status_to_status_code(ps, "none")
        assert code == ""
        assert display == ""


# ── find_cups_printer_name ───────────────────────────────────────────


class TestFindCupsPrinterName:
    """Tests for find_cups_printer_name."""

    @patch(f"{MOD}.shutil.which", return_value=None)
    def test_no_lpstat(self, _m: MagicMock) -> None:
        assert find_cups_printer_name() == ""

    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lpstat")
    def test_found(self, _w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            stdout="device for BrotherHL1110: usb://Brother/HL-1110\n"
        )
        assert find_cups_printer_name() == "BrotherHL1110"

    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lpstat")
    def test_no_brother(self, _w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(stdout="device for HP: ipp://hp.local\n")
        assert find_cups_printer_name() == ""

    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lpstat")
    def test_brother_no_match(self, _w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            stdout="brother printer found but format unexpected\n"
        )
        assert find_cups_printer_name() == ""

    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lpstat")
    def test_timeout(self, _w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired("lpstat", 5)
        assert find_cups_printer_name() == ""

    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lpstat")
    def test_oserror(self, _w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.side_effect = OSError("fail")
        assert find_cups_printer_name() == ""


# ── _parse_cups_usb_uri ─────────────────────────────────────────────


class TestParseCupsUsbUri:
    """Tests for _parse_cups_usb_uri."""

    def test_full_uri(self) -> None:
        info: dict[str, str] = {"product": "", "serial": ""}
        _parse_cups_usb_uri("usb://Brother/HL-1110%20series?serial=ABC123", info)
        assert info["product"] == "HL-1110 series"
        assert info["serial"] == "ABC123"

    def test_no_serial(self) -> None:
        info: dict[str, str] = {"product": "", "serial": ""}
        _parse_cups_usb_uri("usb://Brother/HL-1110", info)
        assert info["product"] == "HL-1110"
        assert info["serial"] == ""


# ── _get_printer_info_from_cups ──────────────────────────────────────


class TestGetPrinterInfoFromCups:
    """Tests for _get_printer_info_from_cups."""

    @patch(f"{MOD}.subprocess.run")
    def test_found(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            stdout="device for B: usb://Brother/HL-1110?serial=XYZ\n"
        )
        result = _get_printer_info_from_cups()
        assert result["product"] == "HL-1110"
        assert result["serial"] == "XYZ"

    @patch(f"{MOD}.subprocess.run")
    def test_no_brother(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(stdout="device for HP: ipp://hp.local\n")
        result = _get_printer_info_from_cups()
        assert result["product"] == ""

    @patch(f"{MOD}.subprocess.run")
    def test_brother_no_usb(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(stdout="device for B: ipp://Brother.local\n")
        result = _get_printer_info_from_cups()
        assert result["product"] == ""

    @patch(f"{MOD}.subprocess.run")
    def test_timeout(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired("lpstat", 5)
        result = _get_printer_info_from_cups()
        assert result["product"] == ""

    @patch(f"{MOD}.subprocess.run")
    def test_oserror(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = OSError("fail")
        result = _get_printer_info_from_cups()
        assert result["product"] == ""
