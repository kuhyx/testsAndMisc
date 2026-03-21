"""Tests for the fetch_license_plates module."""

from __future__ import annotations

import importlib
from pathlib import Path
import sys
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from python_pkg.anki_decks.polish_license_plates.fetch_license_plates import (
    fetch_wikipedia_html,
    get_cache_path,
    is_cache_valid,
    parse_license_plates_from_html,
)


class TestImportError:
    """Tests for the ImportError handling at module level."""

    def test_exits_when_packages_missing(self) -> None:
        """Should exit with error when bs4/requests not installed."""
        module_name = "python_pkg.anki_decks.polish_license_plates.fetch_license_plates"
        # Remove the module so it can be re-imported
        saved_module = sys.modules.pop(module_name)
        # Also remove bs4 to trigger ImportError
        saved_bs4 = sys.modules.pop("bs4", None)
        saved_requests = sys.modules.pop("requests", None)

        import builtins

        original_import = builtins.__import__

        def mock_import(name: str, *args: Any, **kwargs: Any) -> Any:
            if name in ("bs4", "requests"):
                msg = f"No module named '{name}'"
                raise ImportError(msg)
            return original_import(name, *args, **kwargs)

        try:
            with patch("builtins.__import__", side_effect=mock_import):
                with pytest.raises(SystemExit) as exc_info:
                    importlib.import_module(module_name)
                assert exc_info.value.code == 1
        finally:
            # Restore modules
            sys.modules[module_name] = saved_module
            if saved_bs4 is not None:
                sys.modules["bs4"] = saved_bs4
            if saved_requests is not None:
                sys.modules["requests"] = saved_requests


class TestGetCachePath:
    """Tests for get_cache_path."""

    def test_returns_path_in_wikipedia_cache_dir(self) -> None:
        """Cache path should be under .wikipedia_cache directory."""
        result = get_cache_path()
        assert result.name == "license_plates.html"
        assert result.parent.name == ".wikipedia_cache"

    @patch.object(Path, "mkdir")
    def test_creates_cache_directory(self, mock_mkdir: MagicMock) -> None:
        """Should create cache directory with exist_ok=True."""
        get_cache_path()
        mock_mkdir.assert_called_once_with(exist_ok=True)


class TestIsCacheValid:
    """Tests for is_cache_valid."""

    def test_returns_false_when_file_does_not_exist(self, tmp_path: Path) -> None:
        """Should return False when cache file doesn't exist."""
        cache_path = tmp_path / "nonexistent.html"
        assert is_cache_valid(cache_path) is False

    def test_returns_true_when_cache_is_fresh(self, tmp_path: Path) -> None:
        """Should return True when cache file is recent."""
        cache_path = tmp_path / "cache.html"
        cache_path.write_text("cached content")
        assert is_cache_valid(cache_path) is True

    def test_returns_false_when_cache_is_expired(self, tmp_path: Path) -> None:
        """Should return False when cache file is old."""
        cache_path = tmp_path / "cache.html"
        cache_path.write_text("cached content")
        # Mock time to make the file appear old
        with patch(
            "python_pkg.anki_decks.polish_license_plates.fetch_license_plates.time.time",
            return_value=cache_path.stat().st_mtime + 8 * 24 * 60 * 60,
        ):
            assert is_cache_valid(cache_path) is False

    def test_custom_max_age_days(self, tmp_path: Path) -> None:
        """Should use custom max_age_days parameter."""
        cache_path = tmp_path / "cache.html"
        cache_path.write_text("cached content")
        # With max_age_days=0, file should be considered expired
        with patch(
            "python_pkg.anki_decks.polish_license_plates.fetch_license_plates.time.time",
            return_value=cache_path.stat().st_mtime + 1,
        ):
            assert is_cache_valid(cache_path, max_age_days=0) is False


class TestFetchWikipediaHtml:
    """Tests for fetch_wikipedia_html."""

    @patch(
        "python_pkg.anki_decks.polish_license_plates.fetch_license_plates.get_cache_path"
    )
    @patch(
        "python_pkg.anki_decks.polish_license_plates.fetch_license_plates.is_cache_valid",
        return_value=True,
    )
    def test_returns_cached_data_when_valid(
        self,
        _mock_valid: MagicMock,
        mock_cache_path: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Should return cached data when cache is valid."""
        cache_file = tmp_path / "cache.html"
        cache_file.write_text("<html>cached</html>")
        mock_cache_path.return_value = cache_file

        result = fetch_wikipedia_html()
        assert result == "<html>cached</html>"

    @patch(
        "python_pkg.anki_decks.polish_license_plates.fetch_license_plates.get_cache_path"
    )
    @patch(
        "python_pkg.anki_decks.polish_license_plates.fetch_license_plates.is_cache_valid",
        return_value=True,
    )
    @patch(
        "python_pkg.anki_decks.polish_license_plates.fetch_license_plates.requests.get"
    )
    def test_fetches_fresh_when_cache_read_fails(
        self,
        mock_get: MagicMock,
        _mock_valid: MagicMock,
        mock_cache_path: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Should fall through to fetch when cache read raises OSError."""
        tmp_path / "cache.html"
        mock_path = MagicMock(spec=Path)
        mock_path.exists.return_value = True
        mock_stat = MagicMock()
        mock_stat.st_mtime = 0.0
        mock_path.stat.return_value = mock_stat
        mock_path.read_text.side_effect = OSError("read error")
        # write_text should succeed for caching the new response
        mock_path.write_text = MagicMock()
        mock_cache_path.return_value = mock_path

        mock_response = MagicMock()
        mock_response.text = "<html>fresh</html>"
        mock_get.return_value = mock_response

        result = fetch_wikipedia_html()
        assert result == "<html>fresh</html>"
        mock_get.assert_called_once()

    @patch(
        "python_pkg.anki_decks.polish_license_plates.fetch_license_plates.get_cache_path"
    )
    @patch(
        "python_pkg.anki_decks.polish_license_plates.fetch_license_plates.is_cache_valid",
        return_value=False,
    )
    @patch(
        "python_pkg.anki_decks.polish_license_plates.fetch_license_plates.requests.get"
    )
    def test_fetches_from_wikipedia_when_cache_invalid(
        self,
        mock_get: MagicMock,
        _mock_valid: MagicMock,
        mock_cache_path: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Should fetch from Wikipedia when cache is invalid."""
        cache_file = tmp_path / "cache.html"
        mock_cache_path.return_value = cache_file

        mock_response = MagicMock()
        mock_response.text = "<html>wikipedia</html>"
        mock_get.return_value = mock_response

        result = fetch_wikipedia_html()
        assert result == "<html>wikipedia</html>"
        # Should have written cache
        assert cache_file.read_text() == "<html>wikipedia</html>"

    @patch(
        "python_pkg.anki_decks.polish_license_plates.fetch_license_plates.get_cache_path"
    )
    @patch(
        "python_pkg.anki_decks.polish_license_plates.fetch_license_plates.is_cache_valid",
        return_value=False,
    )
    @patch(
        "python_pkg.anki_decks.polish_license_plates.fetch_license_plates.requests.get"
    )
    def test_force_refresh_ignores_cache(
        self,
        mock_get: MagicMock,
        _mock_valid: MagicMock,
        mock_cache_path: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Should fetch from Wikipedia when force_refresh is True."""
        cache_file = tmp_path / "cache.html"
        mock_cache_path.return_value = cache_file

        mock_response = MagicMock()
        mock_response.text = "<html>forced</html>"
        mock_get.return_value = mock_response

        result = fetch_wikipedia_html(force_refresh=True)
        assert result == "<html>forced</html>"

    @patch(
        "python_pkg.anki_decks.polish_license_plates.fetch_license_plates.get_cache_path"
    )
    @patch(
        "python_pkg.anki_decks.polish_license_plates.fetch_license_plates.is_cache_valid",
        return_value=True,
    )
    @patch(
        "python_pkg.anki_decks.polish_license_plates.fetch_license_plates.requests.get"
    )
    def test_force_refresh_skips_valid_cache(
        self,
        mock_get: MagicMock,
        _mock_valid: MagicMock,
        mock_cache_path: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Even with valid cache, force_refresh should fetch fresh."""
        cache_file = tmp_path / "cache.html"
        mock_cache_path.return_value = cache_file

        mock_response = MagicMock()
        mock_response.text = "<html>forced fresh</html>"
        mock_get.return_value = mock_response

        result = fetch_wikipedia_html(force_refresh=True)
        assert result == "<html>forced fresh</html>"
        mock_get.assert_called_once()

    @patch(
        "python_pkg.anki_decks.polish_license_plates.fetch_license_plates.get_cache_path"
    )
    @patch(
        "python_pkg.anki_decks.polish_license_plates.fetch_license_plates.is_cache_valid",
        return_value=False,
    )
    @patch(
        "python_pkg.anki_decks.polish_license_plates.fetch_license_plates.requests.get"
    )
    def test_raises_runtime_error_on_request_exception(
        self,
        mock_get: MagicMock,
        _mock_valid: MagicMock,
        mock_cache_path: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Should raise RuntimeError when requests fails."""
        import requests

        cache_file = tmp_path / "cache.html"
        mock_cache_path.return_value = cache_file
        mock_get.side_effect = requests.RequestException("connection error")

        with pytest.raises(RuntimeError, match="Failed to fetch Wikipedia page"):
            fetch_wikipedia_html()

    @patch(
        "python_pkg.anki_decks.polish_license_plates.fetch_license_plates.get_cache_path"
    )
    @patch(
        "python_pkg.anki_decks.polish_license_plates.fetch_license_plates.is_cache_valid",
        return_value=False,
    )
    @patch(
        "python_pkg.anki_decks.polish_license_plates.fetch_license_plates.requests.get"
    )
    def test_continues_when_cache_write_fails(
        self,
        mock_get: MagicMock,
        _mock_valid: MagicMock,
        mock_cache_path: MagicMock,
    ) -> None:
        """Should return data even when cache write fails."""
        mock_path = MagicMock(spec=Path)
        mock_path.write_text.side_effect = OSError("write error")
        mock_cache_path.return_value = mock_path

        mock_response = MagicMock()
        mock_response.text = "<html>data</html>"
        mock_get.return_value = mock_response

        result = fetch_wikipedia_html()
        assert result == "<html>data</html>"


class TestParseLicensePlatesFromHtml:
    """Tests for parse_license_plates_from_html."""

    def test_raises_error_when_no_tables(self) -> None:
        """Should raise RuntimeError when no wikitable found."""
        html = "<html><body><p>No tables here</p></body></html>"
        with pytest.raises(RuntimeError, match="No wikitable found"):
            parse_license_plates_from_html(html)

    def test_extracts_valid_codes(self) -> None:
        """Should extract valid license plate codes from table."""
        html = """
        <html><body>
        <table class="wikitable">
            <tr><th>Code</th><th>Location</th></tr>
            <tr><td>WA</td><td>Warszawa</td></tr>
            <tr><td>KR</td><td>Kraków</td></tr>
        </table>
        </body></html>
        """
        result = parse_license_plates_from_html(html)
        assert result == {"WA": "Warszawa", "KR": "Kraków"}

    def test_skips_rows_with_too_few_columns(self) -> None:
        """Should skip rows with fewer than MIN_TABLE_COLUMNS cells."""
        html = """
        <html><body>
        <table class="wikitable">
            <tr><th>Code</th><th>Location</th></tr>
            <tr><td>Only one cell</td></tr>
            <tr><td>WA</td><td>Warszawa</td></tr>
        </table>
        </body></html>
        """
        result = parse_license_plates_from_html(html)
        assert result == {"WA": "Warszawa"}

    def test_skips_empty_codes(self) -> None:
        """Should skip entries where code is empty after cleaning."""
        html = """
        <html><body>
        <table class="wikitable">
            <tr><th>Code</th><th>Location</th></tr>
            <tr><td>123</td><td>Some place</td></tr>
            <tr><td>WA</td><td>Warszawa</td></tr>
        </table>
        </body></html>
        """
        result = parse_license_plates_from_html(html)
        assert result == {"WA": "Warszawa"}

    def test_skips_codes_longer_than_max(self) -> None:
        """Should skip codes longer than MAX_CODE_LENGTH."""
        html = """
        <html><body>
        <table class="wikitable">
            <tr><th>Code</th><th>Location</th></tr>
            <tr><td>ABCDE</td><td>Too long code</td></tr>
            <tr><td>WA</td><td>Warszawa</td></tr>
        </table>
        </body></html>
        """
        result = parse_license_plates_from_html(html)
        assert result == {"WA": "Warszawa"}

    def test_skips_empty_locations(self) -> None:
        """Should skip entries with empty location after cleaning."""
        html = """
        <html><body>
        <table class="wikitable">
            <tr><th>Code</th><th>Location</th></tr>
            <tr><td>WA</td><td>   </td></tr>
            <tr><td>KR</td><td>Kraków</td></tr>
        </table>
        </body></html>
        """
        result = parse_license_plates_from_html(html)
        assert result == {"KR": "Kraków"}

    def test_removes_citation_references(self) -> None:
        """Should remove [1], [2] style citations from locations."""
        html = """
        <html><body>
        <table class="wikitable">
            <tr><th>Code</th><th>Location</th></tr>
            <tr><td>WA</td><td>Warszawa[1][23]</td></tr>
        </table>
        </body></html>
        """
        result = parse_license_plates_from_html(html)
        assert result == {"WA": "Warszawa"}

    def test_cleans_whitespace_in_location(self) -> None:
        """Should collapse multiple spaces in location."""
        html = """
        <html><body>
        <table class="wikitable">
            <tr><th>Code</th><th>Location</th></tr>
            <tr><td>WA</td><td>  Warszawa   city  </td></tr>
        </table>
        </body></html>
        """
        result = parse_license_plates_from_html(html)
        assert result == {"WA": "Warszawa city"}

    def test_processes_multiple_tables(self) -> None:
        """Should process all wikitables on the page."""
        html = """
        <html><body>
        <table class="wikitable">
            <tr><th>Code</th><th>Location</th></tr>
            <tr><td>WA</td><td>Warszawa</td></tr>
        </table>
        <table class="wikitable">
            <tr><th>Code</th><th>Location</th></tr>
            <tr><td>KR</td><td>Kraków</td></tr>
        </table>
        </body></html>
        """
        result = parse_license_plates_from_html(html)
        assert result == {"WA": "Warszawa", "KR": "Kraków"}

    def test_uppercases_codes(self) -> None:
        """Should uppercase license plate codes."""
        html = """
        <html><body>
        <table class="wikitable">
            <tr><th>Code</th><th>Location</th></tr>
            <tr><td>wa</td><td>Warszawa</td></tr>
        </table>
        </body></html>
        """
        result = parse_license_plates_from_html(html)
        assert result == {"WA": "Warszawa"}

    def test_removes_non_alpha_from_codes(self) -> None:
        """Should remove non-alphabetic characters from codes."""
        html = """
        <html><body>
        <table class="wikitable">
            <tr><th>Code</th><th>Location</th></tr>
            <tr><td>W-A 1</td><td>Warszawa</td></tr>
        </table>
        </body></html>
        """
        result = parse_license_plates_from_html(html)
        assert result == {"WA": "Warszawa"}

    def test_returns_empty_dict_when_no_valid_entries(self) -> None:
        """Should return empty dict when table has no valid entries."""
        html = """
        <html><body>
        <table class="wikitable">
            <tr><th>Code</th><th>Location</th></tr>
            <tr><td>12345</td><td>Numbers only</td></tr>
        </table>
        </body></html>
        """
        result = parse_license_plates_from_html(html)
        assert result == {}
