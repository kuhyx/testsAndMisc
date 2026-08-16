"""Tests for brother_printer._cups_fallback - economode and state mapping."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

from python_pkg.brother_printer._cups_fallback import (
    _get_cups_economode,
    _map_cups_to_status_code,
)
from python_pkg.brother_printer.constants import (
    _CUPS_REASONS_TO_STATUS,
    get_status_info,
)

MOD = "python_pkg.brother_printer._cups_fallback"


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
