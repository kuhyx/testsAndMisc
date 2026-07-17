"""Tests for brother_printer.constants module."""

from __future__ import annotations

from io import StringIO
from unittest.mock import patch

from python_pkg.brother_printer.constants import (
    BOLD,
    BROTHER_STATUS_CODES,
    BROTHER_USB_VENDOR_ID,
    CYAN,
    DERIVED_TONER_END,
    DIM,
    DRUM_RATED_PAGES,
    GREEN,
    MIN_LPSTAT_JOB_PARTS,
    PROGRESS_BAR_WIDTH,
    RED,
    RESET,
    SNMP_LEVEL_LOW,
    SNMP_LEVEL_OK,
    SUPPLY_LOW_PCT,
    SUPPLY_WARN_PCT,
    TONER_RATED_PAGES,
    YELLOW,
    _out,
    _prompt,
    get_status_info,
)


class TestConstants:
    """Test that constants have expected values."""

    def test_color_codes_are_strings(self) -> None:
        for c in (RED, YELLOW, GREEN, CYAN, BOLD, DIM, RESET):
            assert isinstance(c, str)

    def test_snmp_sentinels(self) -> None:
        assert SNMP_LEVEL_OK == -3
        assert SNMP_LEVEL_LOW == -2

    def test_supply_thresholds(self) -> None:
        assert SUPPLY_LOW_PCT == 10
        assert SUPPLY_WARN_PCT == 25

    def test_progress_bar_width(self) -> None:
        assert PROGRESS_BAR_WIDTH == 25

    def test_page_ratings(self) -> None:
        assert TONER_RATED_PAGES == 1000
        assert DRUM_RATED_PAGES == 10000

    def test_min_lpstat_job_parts(self) -> None:
        assert MIN_LPSTAT_JOB_PARTS == 4

    def test_vendor_id(self) -> None:
        assert BROTHER_USB_VENDOR_ID == 0x04F9


class TestOut:
    """Test _out helper."""

    def test_out_default(self) -> None:
        with patch("sys.stdout", new_callable=StringIO) as mock_out:
            _out()
            assert mock_out.getvalue() == "\n"

    def test_out_with_text(self) -> None:
        with patch("sys.stdout", new_callable=StringIO) as mock_out:
            _out("hello")
            assert mock_out.getvalue() == "hello\n"


class TestPrompt:
    """Test _prompt helper."""

    def test_prompt_reads_input(self) -> None:
        with (
            patch("sys.stdout", new_callable=StringIO),
            patch("sys.stdin", new_callable=StringIO) as mock_in,
        ):
            mock_in.write("answer\n")
            mock_in.seek(0)
            result = _prompt("Enter: ")
            assert result == "answer"


class TestGetStatusInfo:
    """Test get_status_info lookup."""

    def test_known_code(self) -> None:
        severity, text, action = get_status_info("10001")
        assert severity == "ok"
        assert text == "Ready"
        assert action == ""

    def test_toner_low(self) -> None:
        severity, text, _ = get_status_info("40038")
        assert severity == "warn"
        assert "Toner Low" in text

    def test_toner_low_informational_variant(self) -> None:
        """10006 is TONER LOW in the PJL reference, not a benign 'Processing'."""
        severity, text, _ = get_status_info("10006")
        assert severity == "warn"
        assert "Toner Low" in text

    def test_sleep_is_not_an_error(self) -> None:
        """40000 is SLEEP MODE; the reference flags it as explicitly not an error.

        Verified on a real HL-1110, which reports CODE=40000 DISPLAY="SLEEP".
        An earlier table called this a critical Paper Jam.
        """
        severity, text, action = get_status_info("40000")
        assert severity == "ok"
        assert "Sleep" in text
        assert action == ""

    def test_paper_jam_is_40022(self) -> None:
        severity, text, action = get_status_info("40022")
        assert severity == "critical"
        assert text == "Paper Jam"
        assert action != ""

    def test_cover_open_is_40021(self) -> None:
        """Verified on a real HL-1110: CODE=40021 DISPLAY="TOP COVER OPEN"."""
        severity, text, _ = get_status_info("40021")
        assert severity == "critical"
        assert text == "Cover Open"

    def test_out_of_paper_matches_41_family(self) -> None:
        """Verified on a real HL-1110: CODE=41213 DISPLAY="NO PAPER".

        The 41xyy sub-digits do not decode per the HP tray/media tables on this
        printer, so the whole family maps to one meaning.
        """
        severity, text, _ = get_status_info("41213")
        assert severity == "critical"
        assert text == "Out of Paper"

    def test_derived_codes_are_not_pjl(self) -> None:
        """States we infer ourselves must not masquerade as printer reports."""
        severity, text, _ = get_status_info(DERIVED_TONER_END)
        assert severity == "critical"
        assert "estimated" in text.lower()

    def test_invented_codes_are_unknown(self) -> None:
        """Codes absent from the PJL reference must not be given invented meanings."""
        for code in ("40310", "40300", "42000", "30038", "40201"):
            severity, text, _ = get_status_info(code)
            assert severity == "info"
            assert "Unknown" in text

    def test_unknown_code(self) -> None:
        severity, text, action = get_status_info("99999")
        assert severity == "info"
        assert "Unknown" in text
        assert action != ""

    def test_invalid_code(self) -> None:
        severity, text, _ = get_status_info("not_a_number")
        assert severity == "info"
        assert "Unknown" in text

    def test_all_codes_present(self) -> None:
        assert len(BROTHER_STATUS_CODES) > 0
        for sev, text, action in BROTHER_STATUS_CODES.values():
            assert sev in ("ok", "info", "warn", "critical")
            assert isinstance(text, str)
            assert isinstance(action, str)
