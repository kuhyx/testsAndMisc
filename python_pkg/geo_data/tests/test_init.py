"""Tests for python_pkg.geo_data.__init__ module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from python_pkg.geo_data import (
    clear_cache,
    download_all_poland_data,
    download_all_warsaw_data,
)


class TestDownloadAllWarsawData:
    """Tests for download_all_warsaw_data."""

    @patch("python_pkg.geo_data.get_warsaw_osiedla")
    @patch("python_pkg.geo_data.get_warsaw_landmarks")
    @patch("python_pkg.geo_data.get_warsaw_streets")
    @patch("python_pkg.geo_data.get_warsaw_metro_stations")
    @patch("python_pkg.geo_data.get_warsaw_bridges")
    @patch("python_pkg.geo_data.get_vistula_river")
    @patch("python_pkg.geo_data.get_warsaw_boundary")
    @patch("python_pkg.geo_data.sys.stdout")
    def test_calls_all_warsaw_functions(
        self,
        mock_stdout: MagicMock,
        mock_boundary: MagicMock,
        mock_vistula: MagicMock,
        mock_bridges: MagicMock,
        mock_metro: MagicMock,
        mock_streets: MagicMock,
        mock_landmarks: MagicMock,
        mock_osiedla: MagicMock,
    ) -> None:
        download_all_warsaw_data()
        mock_boundary.assert_called_once()
        mock_vistula.assert_called_once()
        mock_bridges.assert_called_once()
        mock_metro.assert_called_once()
        mock_streets.assert_called_once()
        mock_landmarks.assert_called_once()
        mock_osiedla.assert_called_once()


class TestDownloadAllPolandData:
    """Tests for download_all_poland_data."""

    @patch("python_pkg.geo_data.get_poland_boundary")
    @patch("python_pkg.geo_data.get_polish_gminy")
    @patch("python_pkg.geo_data.get_polish_powiaty")
    @patch("python_pkg.geo_data.get_polish_wojewodztwa")
    @patch("python_pkg.geo_data.sys.stdout")
    def test_calls_all_poland_functions(
        self,
        mock_stdout: MagicMock,
        mock_woj: MagicMock,
        mock_powiaty: MagicMock,
        mock_gminy: MagicMock,
        mock_boundary: MagicMock,
    ) -> None:
        download_all_poland_data()
        mock_woj.assert_called_once()
        mock_powiaty.assert_called_once()
        mock_gminy.assert_called_once()
        mock_boundary.assert_called_once()


class TestClearCache:
    """Tests for clear_cache."""

    @patch("python_pkg.geo_data.shutil.rmtree")
    @patch("python_pkg.geo_data.CACHE_DIR")
    @patch("python_pkg.geo_data.sys.stdout")
    def test_cache_exists(
        self,
        mock_stdout: MagicMock,
        mock_cache_dir: MagicMock,
        mock_rmtree: MagicMock,
    ) -> None:
        mock_cache_dir.exists.return_value = True
        clear_cache()
        mock_rmtree.assert_called_once_with(mock_cache_dir)

    @patch("python_pkg.geo_data.CACHE_DIR")
    @patch("python_pkg.geo_data.sys.stdout")
    def test_cache_not_exists(
        self,
        mock_stdout: MagicMock,
        mock_cache_dir: MagicMock,
    ) -> None:
        mock_cache_dir.exists.return_value = False
        clear_cache()
