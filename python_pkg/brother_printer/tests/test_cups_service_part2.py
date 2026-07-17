"""Tests for brother_printer.cups_service module - part 2."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

from python_pkg.brother_printer.constants import (
    _CUPS_REASONS_TO_STATUS,
    DERIVED_CUPS_ERROR,
    get_status_info,
)
from python_pkg.brother_printer.cups_service import (
    _cups_reasons_to_error,
    _get_cups_economode,
    _map_cups_to_status_code,
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
    def test_no_lpoptions(self, m: MagicMock) -> None:
        assert _get_cups_economode("Brother") == ""

    @patch("python_pkg.brother_printer._query.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lpoptions")
    def test_economode_on(self, w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            stdout="BREconomode/Toner Save Mode: *True False\n"
        )
        assert _get_cups_economode("Brother") == "ON"

    @patch("python_pkg.brother_printer._query.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lpoptions")
    def test_economode_off(self, w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            stdout="BREconomode/Toner Save Mode: True *False\n"
        )
        assert _get_cups_economode("Brother") == "OFF"

    @patch("python_pkg.brother_printer._query.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lpoptions")
    def test_no_economode_line(self, w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            stdout="Resolution/Output Resolution: 600dpi *1200dpi\n"
        )
        assert _get_cups_economode("Brother") == ""

    @patch("python_pkg.brother_printer._query.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lpoptions")
    def test_economode_no_star_match(self, w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            stdout="BREconomode/Toner Save Mode: True False\n"
        )
        assert _get_cups_economode("Brother") == ""

    @patch("python_pkg.brother_printer._query.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lpoptions")
    def test_timeout(self, w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired("lpoptions", 5)
        assert _get_cups_economode("Brother") == ""

    @patch("python_pkg.brother_printer._query.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lpoptions")
    def test_oserror(self, w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.side_effect = OSError("fail")
        assert _get_cups_economode("Brother") == ""


# ── _map_cups_to_status_code ─────────────────────────────────────────


class TestMapCupsToStatusCode:
    """Tests for _map_cups_to_status_code.

    Every code here must exist in BROTHER_STATUS_CODES; mapping CUPS onto a
    code the table does not know silently degrades to "unknown status".
    """

    def test_reason_match(self) -> None:
        assert _map_cups_to_status_code("idle", "toner-low-report") == "40038"

    def test_state_match(self) -> None:
        assert _map_cups_to_status_code("idle", "none") == "10001"

    def test_processing_state(self) -> None:
        assert _map_cups_to_status_code("processing", "none") == "10023"

    def test_stopped_state(self) -> None:
        assert _map_cups_to_status_code("stopped", "none") == "40079"

    def test_unknown_state(self) -> None:
        assert _map_cups_to_status_code("mystery", "none") == "10001"

    def test_state_with_parenthetical(self) -> None:
        assert _map_cups_to_status_code("idle (on fire)", "none") == "10001"

    def test_every_mapped_code_is_resolvable(self) -> None:
        """Guard the class of bug where a mapping points at a deleted code."""
        for state in ("idle", "processing", "stopped"):
            code = _map_cups_to_status_code(state, "none")
            _, text, _ = get_status_info(code)
            assert "Unknown" not in text
        for reason in _CUPS_REASONS_TO_STATUS:
            code = _map_cups_to_status_code("idle", reason)
            _, text, _ = get_status_info(code)
            assert "Unknown" not in text


# ── _cups_reasons_to_error ───────────────────────────────────────────


class TestCupsReasonsToError:
    """Tests for _cups_reasons_to_error."""

    def test_media_jam(self) -> None:
        """A real jam is 40022. It used to map to 40000, which is Sleep."""
        code, display = _cups_reasons_to_error("media-jam-report")
        assert code == "40022"
        assert display == "Paper Jam"

    def test_cover_open(self) -> None:
        code, _ = _cups_reasons_to_error("cover-open")
        assert code == "40021"

    def test_door_open(self) -> None:
        code, _ = _cups_reasons_to_error("door-open")
        assert code == "40021"

    def test_toner_empty(self) -> None:
        code, _ = _cups_reasons_to_error("toner-empty")
        assert code == "40010"

    def test_toner_low(self) -> None:
        code, _ = _cups_reasons_to_error("toner-low")
        assert code == "40038"

    def test_unknown_reason_shows_what_cups_said(self) -> None:
        """'Printer Error' alone is useless; quote the reason we were given."""
        code, display = _cups_reasons_to_error("something-weird")
        assert code == DERIVED_CUPS_ERROR
        assert "something-weird" in display

    def test_no_reason_at_all(self) -> None:
        code, display = _cups_reasons_to_error("none")
        assert code == DERIVED_CUPS_ERROR
        assert "no reason" in display.lower()

    def test_every_error_code_is_resolvable(self) -> None:
        for reason in ("media-jam", "cover-open", "toner-empty", "toner-low"):
            code, _ = _cups_reasons_to_error(reason)
            _, text, _ = get_status_info(code)
            assert "Unknown" not in text


# ── _port_status_to_status_code ──────────────────────────────────────


class TestPortStatusToStatusCode:
    """Tests for _port_status_to_status_code.

    The port status only exposes paper/error/online bits, so it must not
    pretend to know more than that - it previously reported "Cover Open" for
    any error on an offline printer, which was a guess.
    """

    def test_error_and_paper_empty(self) -> None:
        ps = USBPortStatus(error=True, paper_empty=True, online=True)
        code, display = _port_status_to_status_code(ps, "none")
        assert code == "41000"
        assert display == "No Paper"

    def test_error_and_not_online_defers_to_cups(self) -> None:
        ps = USBPortStatus(error=True, paper_empty=False, online=False)
        code, display = _port_status_to_status_code(ps, "cover-open")
        assert code == "40021"
        assert display == "Cover Open"

    def test_error_with_no_clue_does_not_guess(self) -> None:
        ps = USBPortStatus(error=True, paper_empty=False, online=False)
        code, _ = _port_status_to_status_code(ps, "none")
        assert code == DERIVED_CUPS_ERROR

    def test_error_only(self) -> None:
        ps = USBPortStatus(error=True, paper_empty=False, online=True)
        code, _ = _port_status_to_status_code(ps, "media-jam")
        assert code == "40022"

    def test_paper_empty_no_error(self) -> None:
        ps = USBPortStatus(error=False, paper_empty=True, online=True)
        code, _ = _port_status_to_status_code(ps, "none")
        assert code == "41000"

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
    def test_no_lpstat(self, m: MagicMock) -> None:
        assert find_cups_printer_name() == ""

    @patch("python_pkg.brother_printer._query.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lpstat")
    def test_found(self, w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            stdout="device for BrotherHL1110: usb://Brother/HL-1110\n"
        )
        assert find_cups_printer_name() == "BrotherHL1110"

    @patch("python_pkg.brother_printer._query.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lpstat")
    def test_no_brother(self, w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(stdout="device for HP: ipp://hp.local\n")
        assert find_cups_printer_name() == ""

    @patch("python_pkg.brother_printer._query.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lpstat")
    def test_brother_no_match(self, w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            stdout="brother printer found but format unexpected\n"
        )
        assert find_cups_printer_name() == ""

    @patch("python_pkg.brother_printer._query.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lpstat")
    def test_timeout(self, w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired("lpstat", 5)
        assert find_cups_printer_name() == ""

    @patch("python_pkg.brother_printer._query.subprocess.run")
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/lpstat")
    def test_oserror(self, w: MagicMock, mock_run: MagicMock) -> None:
        mock_run.side_effect = OSError("fail")
        assert find_cups_printer_name() == ""
