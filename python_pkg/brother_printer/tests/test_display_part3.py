"""Tests for brother_printer.display - page counts and dropped-page warning."""

from __future__ import annotations

from io import StringIO
from unittest.mock import MagicMock, patch

from python_pkg.brother_printer.data_classes import (
    PageCountEstimate,
    PageDeliveryCheck,
)
from python_pkg.brother_printer.display import (
    _display_consumables_reference,
    _display_page_count_estimate,
    _display_page_delivery_warning,
)

MOD = "python_pkg.brother_printer.display"


class TestDisplayPageCountEstimate:
    @patch(f"{MOD}.estimate_consumable_life")
    def test_no_pages(self, mock_est: MagicMock) -> None:
        mock_est.return_value = PageCountEstimate(total_pages=0)
        with patch("sys.stdout", new_callable=StringIO) as out:
            _display_page_count_estimate()
            assert out.getvalue() == ""

    @patch(f"{MOD}.estimate_consumable_life")
    def test_printer_count_passed_through(self, mock_est: MagicMock) -> None:
        mock_est.return_value = PageCountEstimate(total_pages=2017)
        with patch("sys.stdout", new_callable=StringIO):
            _display_page_count_estimate(2017)
        mock_est.assert_called_once_with(2017)

    @patch(f"{MOD}.estimate_consumable_life")
    def test_approximate_is_labelled(self, mock_est: MagicMock) -> None:
        """A CUPS-log figure must not be presented as the printer's own count."""
        mock_est.return_value = PageCountEstimate(
            total_pages=1658,
            toner_pages=250,
            drum_pages=1658,
            approximate=True,
        )
        with patch("sys.stdout", new_callable=StringIO) as out:
            _display_page_count_estimate(0)
        assert "Approximate" in out.getvalue()

    @patch(f"{MOD}.estimate_consumable_life")
    def test_printer_count_is_not_labelled_approximate(
        self,
        mock_est: MagicMock,
    ) -> None:
        mock_est.return_value = PageCountEstimate(
            total_pages=2017,
            toner_pages=250,
            drum_pages=2017,
            approximate=False,
        )
        with patch("sys.stdout", new_callable=StringIO) as out:
            _display_page_count_estimate(2017)
        assert "Approximate" not in out.getvalue()

    @patch(f"{MOD}.estimate_consumable_life")
    def test_healthy(self, mock_est: MagicMock) -> None:
        mock_est.return_value = PageCountEstimate(
            total_pages=100,
            toner_pages=100,
            drum_pages=100,
            toner_pct_remaining=90,
            drum_pct_remaining=99,
        )
        with patch("sys.stdout", new_callable=StringIO) as out:
            _display_page_count_estimate()
            assert "Total pages" in out.getvalue()

    @patch(f"{MOD}.estimate_consumable_life")
    def test_toner_exhausted(self, mock_est: MagicMock) -> None:
        mock_est.return_value = PageCountEstimate(
            total_pages=1000,
            toner_pages=1000,
            drum_pages=100,
            toner_pct_remaining=0,
            drum_pct_remaining=99,
            toner_exhausted=True,
            toner_low=True,
        )
        with patch("sys.stdout", new_callable=StringIO) as out:
            _display_page_count_estimate()
            assert "REPLACE NOW" in out.getvalue()

    @patch(f"{MOD}.estimate_consumable_life")
    def test_toner_low(self, mock_est: MagicMock) -> None:
        mock_est.return_value = PageCountEstimate(
            total_pages=800,
            toner_pages=800,
            drum_pages=100,
            toner_pct_remaining=20,
            drum_pct_remaining=99,
            toner_low=True,
        )
        with patch("sys.stdout", new_callable=StringIO) as out:
            _display_page_count_estimate()
            assert "order soon" in out.getvalue()

    @patch(f"{MOD}.estimate_consumable_life")
    def test_drum_near_end(self, mock_est: MagicMock) -> None:
        mock_est.return_value = PageCountEstimate(
            total_pages=9000,
            toner_pages=100,
            drum_pages=9000,
            toner_pct_remaining=90,
            drum_pct_remaining=10,
            drum_near_end=True,
        )
        with patch("sys.stdout", new_callable=StringIO) as out:
            _display_page_count_estimate()
            assert "nearing end" in out.getvalue()


class TestDisplayConsumablesReference:
    def test_prints(self) -> None:
        with patch("sys.stdout", new_callable=StringIO) as out:
            _display_consumables_reference()
            assert "TN-1050" in out.getvalue()


class TestDisplayPageDeliveryWarning:
    """Surfacing pages the printer dropped without telling anyone."""

    @patch(f"{MOD}.check_page_delivery")
    def test_warns_with_actionable_fix(self, mock_check: MagicMock) -> None:
        mock_check.return_value = PageDeliveryCheck(
            cups_pages=63,
            printer_pages=3,
            dropped=60,
            suspected=True,
        )
        with patch("sys.stdout", new_callable=StringIO) as out:
            _display_page_delivery_warning(2087, queue_idle=True)
        printed = out.getvalue()
        assert "60 pages did not print" in printed
        assert "63" in printed
        # Useless without telling the reader what to actually do about it.
        assert "Resolution=300dpi" in printed

    @patch(f"{MOD}.check_page_delivery")
    def test_silent_when_healthy(self, mock_check: MagicMock) -> None:
        mock_check.return_value = PageDeliveryCheck(suspected=False)
        with patch("sys.stdout", new_callable=StringIO) as out:
            _display_page_delivery_warning(2087, queue_idle=True)
        assert out.getvalue() == ""

    @patch(f"{MOD}.check_page_delivery")
    def test_passes_queue_state_through(self, mock_check: MagicMock) -> None:
        mock_check.return_value = PageDeliveryCheck(suspected=False)
        with patch("sys.stdout", new_callable=StringIO):
            _display_page_delivery_warning(2087, queue_idle=False)
        mock_check.assert_called_once_with(2087, queue_idle=False)
