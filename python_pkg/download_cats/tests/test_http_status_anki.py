"""Unit tests for HTTP status code Anki generator."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from python_pkg.download_cats.http_status_anki import (
    CACHE_DIR,
    HTTP_STATUS_CODES,
    REQUEST_TIMEOUT,
    _download_cat_image,
    _get_cached_image_path,
    generate_anki_package,
    get_or_download_image,
    main,
)


class TestDownloadCatImage:
    """Tests for _download_cat_image function."""

    def test_successful_download(self) -> None:
        """Test successful image download."""
        status_code = 200
        image_content = b"fake cat image"

        mock_response = MagicMock()
        mock_response.content = image_content

        with patch("requests.get", return_value=mock_response) as mock_get:
            result = _download_cat_image(status_code)

            mock_get.assert_called_once_with(
                "https://http.cat/200.jpg",
                timeout=REQUEST_TIMEOUT,
            )
            mock_response.raise_for_status.assert_called_once()
            assert result == image_content

    def test_http_error_raised(self) -> None:
        """Test that HTTP errors are raised."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "404 Not Found"
        )

        with (
            patch("requests.get", return_value=mock_response),
            pytest.raises(requests.exceptions.HTTPError),
        ):
            _download_cat_image(404)

    def test_connection_error_raised(self) -> None:
        """Test that connection errors are raised."""
        with (
            patch(
                "requests.get",
                side_effect=requests.exceptions.ConnectionError("Network error"),
            ),
            pytest.raises(requests.exceptions.ConnectionError),
        ):
            _download_cat_image(500)


class TestGetCachedImagePath:
    """Tests for _get_cached_image_path function."""

    def test_returns_correct_path(self) -> None:
        """Test that correct cache path is returned."""
        status_code = 200
        expected_path = CACHE_DIR / "200.jpg"

        result = _get_cached_image_path(status_code)

        assert result == expected_path

    def test_different_codes_different_paths(self) -> None:
        """Test that different status codes get different paths."""
        path_200 = _get_cached_image_path(200)
        path_404 = _get_cached_image_path(404)

        assert path_200 != path_404
        assert "200.jpg" in str(path_200)
        assert "404.jpg" in str(path_404)


class TestGetOrDownloadImage:
    """Tests for get_or_download_image function."""

    def test_uses_cache_when_available(self) -> None:
        """Test that cached image is used when available."""
        status_code = 200
        cached_content = b"cached image"

        with (
            patch(
                "pathlib.Path.exists",
                return_value=True,
            ),
            patch(
                "pathlib.Path.read_bytes",
                return_value=cached_content,
            ),
            patch(
                "python_pkg.download_cats.http_status_anki._download_cat_image"
            ) as mock_download,
        ):
            result = get_or_download_image(status_code, use_cache=True)

            assert result == cached_content
            mock_download.assert_not_called()

    def test_downloads_when_not_cached(self) -> None:
        """Test that image is downloaded when not in cache."""
        status_code = 404
        downloaded_content = b"downloaded image"

        with (
            patch("pathlib.Path.exists", return_value=False),
            patch("pathlib.Path.mkdir"),
            patch(
                "python_pkg.download_cats.http_status_anki._download_cat_image",
                return_value=downloaded_content,
            ) as mock_download,
            patch("pathlib.Path.write_bytes") as mock_write,
        ):
            result = get_or_download_image(status_code, use_cache=True)

            assert result == downloaded_content
            mock_download.assert_called_once_with(status_code)
            mock_write.assert_called_once_with(downloaded_content)

    def test_ignores_cache_when_disabled(self) -> None:
        """Test that cache is ignored when use_cache=False."""
        status_code = 200
        downloaded_content = b"fresh download"

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.mkdir"),
            patch(
                "python_pkg.download_cats.http_status_anki._download_cat_image",
                return_value=downloaded_content,
            ) as mock_download,
            patch("pathlib.Path.write_bytes"),
        ):
            result = get_or_download_image(status_code, use_cache=False)

            assert result == downloaded_content
            mock_download.assert_called_once_with(status_code)

    def test_creates_cache_directory(self) -> None:
        """Test that cache directory is created if it doesn't exist."""
        with (
            patch("pathlib.Path.exists", return_value=False),
            patch("pathlib.Path.mkdir") as mock_mkdir,
            patch(
                "python_pkg.download_cats.http_status_anki._download_cat_image",
                return_value=b"image",
            ),
            patch("pathlib.Path.write_bytes"),
        ):
            get_or_download_image(200, use_cache=True)

            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)


class TestGenerateAnkiPackage:
    """Tests for generate_anki_package function."""

    def test_creates_package_with_all_codes(self) -> None:
        """Test that package is created with cards for all status codes."""
        test_codes = {200: "OK", 404: "Not Found"}

        with (
            patch(
                "python_pkg.download_cats.http_status_anki.get_or_download_image",
                return_value=b"fake image",
            ),
            patch("pathlib.Path.write_bytes"),
        ):
            package = generate_anki_package(test_codes, use_cache=True)

            # Should have 2 cards per status code (bidirectional)
            assert len(package.decks[0].notes) == 4

    def test_uses_correct_deck_name(self) -> None:
        """Test that deck uses specified name."""
        test_codes = {200: "OK"}
        deck_name = "Test Deck"

        with (
            patch(
                "python_pkg.download_cats.http_status_anki.get_or_download_image",
                return_value=b"fake image",
            ),
            patch("pathlib.Path.write_bytes"),
        ):
            package = generate_anki_package(test_codes, deck_name, use_cache=True)

            assert package.decks[0].name == deck_name

    def test_handles_download_errors(self) -> None:
        """Test that download errors are handled gracefully."""
        test_codes = {200: "OK", 404: "Not Found"}

        def mock_download(code: int, *, use_cache: bool) -> bytes:
            del use_cache  # Intentionally unused in test mock
            error_msg = "Failed"
            if code == 404:
                raise requests.exceptions.RequestException(error_msg)
            return b"image"

        with (
            patch(
                "python_pkg.download_cats.http_status_anki.get_or_download_image",
                side_effect=mock_download,
            ),
            patch("pathlib.Path.write_bytes"),
        ):
            package = generate_anki_package(test_codes, use_cache=True)

            # Should only have cards for successful downloads (200)
            assert len(package.decks[0].notes) == 2  # 2 cards for status 200

    def test_creates_media_files(self) -> None:
        """Test that media files are created for images."""
        test_codes = {200: "OK"}

        with (
            patch(
                "python_pkg.download_cats.http_status_anki.get_or_download_image",
                return_value=b"fake image",
            ),
            patch("pathlib.Path.write_bytes"),
        ):
            package = generate_anki_package(test_codes, use_cache=True)

            assert len(package.media_files) == 1
            assert "http_cat_200.jpg" in package.media_files[0]

    def test_respects_cache_setting(self) -> None:
        """Test that cache setting is passed to download function."""
        test_codes = {200: "OK"}

        with (
            patch(
                "python_pkg.download_cats.http_status_anki.get_or_download_image",
                return_value=b"fake image",
            ) as mock_get,
            patch("pathlib.Path.write_bytes"),
        ):
            generate_anki_package(test_codes, use_cache=False)

            mock_get.assert_called_with(200, use_cache=False)


class TestMain:
    """Tests for main function."""

    def test_default_output_path(self) -> None:
        """Test that default output path is used."""
        with patch(
            "python_pkg.download_cats.http_status_anki.generate_anki_package"
        ) as mock_gen:
            mock_package = MagicMock()
            mock_gen.return_value = mock_package

            result = main([])

            assert result == 0
            # Check that write_to_file was called with default path
            call_args = mock_package.write_to_file.call_args[0][0]
            assert "http_status_codes.apkg" in call_args

    def test_custom_output_path(self) -> None:
        """Test that custom output path is used."""
        with patch(
            "python_pkg.download_cats.http_status_anki.generate_anki_package"
        ) as mock_gen:
            mock_package = MagicMock()
            mock_gen.return_value = mock_package

            result = main(["--output", "custom.apkg"])

            assert result == 0
            call_args = mock_package.write_to_file.call_args[0][0]
            assert "custom.apkg" in call_args

    def test_custom_deck_name(self) -> None:
        """Test that custom deck name is used."""
        with patch(
            "python_pkg.download_cats.http_status_anki.generate_anki_package"
        ) as mock_gen:
            mock_package = MagicMock()
            mock_gen.return_value = mock_package

            main(["--deck-name", "My Custom Deck"])

            mock_gen.assert_called_once()
            assert mock_gen.call_args[0][1] == "My Custom Deck"

    def test_no_cache_option(self) -> None:
        """Test that --no-cache option disables caching."""
        with patch(
            "python_pkg.download_cats.http_status_anki.generate_anki_package"
        ) as mock_gen:
            mock_package = MagicMock()
            mock_gen.return_value = mock_package

            main(["--no-cache"])

            # use_cache should be False (not args.no_cache = True)
            assert mock_gen.call_args[1]["use_cache"] is False

    def test_error_handling(self) -> None:
        """Test that errors are handled gracefully."""
        with patch(
            "python_pkg.download_cats.http_status_anki.generate_anki_package",
            side_effect=RuntimeError("Test error"),
        ):
            result = main([])

            assert result == 1

    def test_verbose_logging(self) -> None:
        """Test that verbose flag enables logging."""
        with (
            patch(
                "python_pkg.download_cats.http_status_anki.generate_anki_package"
            ) as mock_gen,
            patch("logging.basicConfig") as mock_config,
        ):
            mock_package = MagicMock()
            mock_gen.return_value = mock_package

            main(["--verbose"])

            # Check that logging was configured
            mock_config.assert_called_once()
            call_kwargs = mock_config.call_args[1]
            assert call_kwargs["level"] == 20  # logging.INFO


class TestConstants:
    """Tests for module constants."""

    def test_http_status_codes_not_empty(self) -> None:
        """Test that HTTP_STATUS_CODES is populated."""
        assert len(HTTP_STATUS_CODES) > 0

    def test_common_status_codes_present(self) -> None:
        """Test that common status codes are present."""
        common_codes = [200, 201, 301, 400, 401, 403, 404, 500, 502, 503]
        for code in common_codes:
            assert code in HTTP_STATUS_CODES

    def test_status_codes_have_descriptions(self) -> None:
        """Test that all status codes have non-empty descriptions."""
        for code, description in HTTP_STATUS_CODES.items():
            assert isinstance(code, int)
            assert isinstance(description, str)
            assert len(description) > 0

    def test_request_timeout_value(self) -> None:
        """Test REQUEST_TIMEOUT constant has expected value."""
        assert REQUEST_TIMEOUT == 30

    def test_cache_dir_path(self) -> None:
        """Test that CACHE_DIR is properly configured."""
        assert isinstance(CACHE_DIR, Path)
        assert "http_cat_cache" in str(CACHE_DIR)
