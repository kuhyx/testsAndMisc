"""Tests for brother_printer.constants module."""

from __future__ import annotations

from io import StringIO
from unittest.mock import patch

from python_pkg.brother_printer.constants import (
    BOLD,
    BROTHER_STATUS_CODES,
    BROTHER_USB_VENDOR_ID,
    CYAN,
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
        severity, text, _ = get_status_info("30010")
        assert severity == "warn"
        assert "Toner Low" in text

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
