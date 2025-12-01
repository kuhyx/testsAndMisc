"""Unit tests for generate_cats module."""

from unittest.mock import MagicMock, mock_open, patch

import requests

from python_pkg.download_cats.generate_cats import (
    MAX_REQUESTS,
    REQUEST_TIMEOUT,
    _download_single_image,
    main,
)


class TestDownloadSingleImage:
    """Tests for _download_single_image function."""

    def test_successful_download(self) -> None:
        """Test successful image download and save."""
        image_url = "https://example.com/cat.jpg"
        image_content = b"fake image content"

        mock_response = MagicMock()
        mock_response.content = image_content

        with (
            patch("requests.get", return_value=mock_response) as mock_get,
            patch("pathlib.Path.open", mock_open()) as mock_file,
        ):
            _download_single_image(image_url)

            mock_get.assert_called_once_with(image_url, timeout=REQUEST_TIMEOUT)
            mock_response.raise_for_status.assert_called_once()
            mock_file().write.assert_called_once_with(image_content)

    def test_request_exception_logged(self) -> None:
        """Test that request exceptions are logged."""
        image_url = "https://example.com/cat.jpg"

        with (
            patch(
                "requests.get",
                side_effect=requests.exceptions.RequestException("Connection error"),
            ),
            patch("python_pkg.download_cats.generate_cats._logger") as mock_logger,
        ):
            _download_single_image(image_url)

            mock_logger.exception.assert_called_once()
            call_args = mock_logger.exception.call_args
            assert "Failed to download" in call_args[0][0]

    def test_http_error_logged(self) -> None:
        """Test that HTTP errors are logged."""
        image_url = "https://example.com/cat.jpg"

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "404 Not Found"
        )

        with (
            patch("requests.get", return_value=mock_response),
            patch("python_pkg.download_cats.generate_cats._logger") as mock_logger,
        ):
            _download_single_image(image_url)

            mock_logger.exception.assert_called_once()


class TestMain:
    """Tests for main function."""

    def test_creates_output_directory(self) -> None:
        """Test that main creates CATS2 directory."""
        mock_api_response = MagicMock()
        mock_api_response.text = "[]"  # Empty response

        with (
            patch("requests.get", return_value=mock_api_response),
            patch("pathlib.Path.mkdir") as mock_mkdir,
        ):
            main()

            # Should create directory for each batch
            assert mock_mkdir.call_count >= 1
            mock_mkdir.assert_called_with(parents=True, exist_ok=True)

    def test_sends_correct_number_of_requests(self) -> None:
        """Test that main sends MAX_REQUESTS API requests."""
        mock_api_response = MagicMock()
        mock_api_response.text = "[]"

        with patch("requests.get", return_value=mock_api_response) as mock_get:
            main()

            assert mock_get.call_count == MAX_REQUESTS

    def test_downloads_images_from_response(self) -> None:
        """Test that main downloads images from API response."""
        mock_api_response = MagicMock()
        mock_api_response.text = '[{"url": "https://cats.com/1.jpg"}]'

        with (
            patch("requests.get", return_value=mock_api_response),
            patch("pathlib.Path.mkdir"),
            patch(
                "python_pkg.download_cats.generate_cats._download_single_image"
            ) as mock_dl,
        ):
            main()

            # Called once per image, per request batch
            assert mock_dl.call_count == MAX_REQUESTS
            mock_dl.assert_called_with("https://cats.com/1.jpg")

    def test_handles_multiple_images_in_response(self) -> None:
        """Test handling multiple images in single API response."""
        mock_api_response = MagicMock()
        mock_api_response.text = (
            '[{"url": "https://cats.com/1.jpg"}, {"url": "https://cats.com/2.jpg"}]'
        )

        with (
            patch("requests.get", return_value=mock_api_response),
            patch("pathlib.Path.mkdir"),
            patch(
                "python_pkg.download_cats.generate_cats._download_single_image"
            ) as mock_dl,
        ):
            main()

            # 2 images per response x MAX_REQUESTS batches
            assert mock_dl.call_count == 2 * MAX_REQUESTS


class TestConstants:
    """Tests for module constants."""

    def test_max_requests_value(self) -> None:
        """Test MAX_REQUESTS constant has expected value."""
        assert MAX_REQUESTS == 90

    def test_request_timeout_value(self) -> None:
        """Test REQUEST_TIMEOUT constant has expected value."""
        assert REQUEST_TIMEOUT == 30
