"""Tests for brother_printer._cups_fallback - status mapping and discovery.

Split from test_cups_service_part2.py under the 250-line cap. These cover the
mapping from what CUPS says went wrong onto the Brother PJL status codes the
report displays, plus finding the Brother queue name.
"""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

from python_pkg.brother_printer._cups_fallback import (
    _cups_reasons_to_error,
    _port_status_to_status_code,
    find_cups_printer_name,
)
from python_pkg.brother_printer.constants import (
    DERIVED_CUPS_ERROR,
    get_status_info,
)
from python_pkg.brother_printer.data_classes import USBPortStatus

MOD = "python_pkg.brother_printer._cups_fallback"


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
