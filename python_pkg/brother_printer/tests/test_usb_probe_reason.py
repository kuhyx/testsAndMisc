"""Tests for cups_service._usb_probe_skip_reason - the fallback note's reason."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from python_pkg.brother_printer.cups_service import _usb_probe_skip_reason

MOD = "python_pkg.brother_printer.cups_service"


class TestUsbProbeSkipReason:
    """The note must name the real reason, not blame a pyusb that is there."""

    def test_busy_cups_wins(self) -> None:
        reason = _usb_probe_skip_reason("processing")
        assert "CUPS has a job" in reason

    @patch(f"{MOD}._import_or_raise", side_effect=ImportError("usb.core"))
    def test_pyusb_missing(self, m: MagicMock) -> None:
        assert "pyusb not installed" in _usb_probe_skip_reason("idle")

    @patch(f"{MOD}._import_or_raise", return_value=MagicMock())
    def test_printer_silent(self, m: MagicMock) -> None:
        assert "did not answer" in _usb_probe_skip_reason("idle")
