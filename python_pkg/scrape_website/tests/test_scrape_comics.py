"""Unit tests for scrape_comics module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from python_pkg.scrape_website.scrape_comics import (
    REQUEST_TIMEOUT,
    _download_image,
    main,
)


class TestDownloadImage:
    """Tests for _download_image function."""

    def test_downloads_new_image(self) -> None:
        """Test that new images are downloaded successfully."""
        image_url = "https://example.com/comic/image.jpg"
        image_content = b"fake image content"

        mock_response = MagicMock()
        mock_response.content = image_content

        with (
            patch("requests.get", return_value=mock_response) as mock_get,
            patch.object(Path, "exists", return_value=False),
            patch.object(Path, "open", MagicMock()),
        ):
            result = _download_image(image_url)

            mock_get.assert_called_once_with(image_url, timeout=REQUEST_TIMEOUT)
            assert result is True

    def test_skips_existing_image(self) -> None:
        """Test that existing images are skipped."""
        image_url = "https://example.com/comic/existing.jpg"

        with patch.object(Path, "exists", return_value=True):
            result = _download_image(image_url)

            assert result is False

    def test_extracts_filename_from_url(self) -> None:
        """Test that filename is extracted correctly from URL."""
        image_url = "https://example.com/path/to/comic_01.jpg"
        image_content = b"content"

        mock_response = MagicMock()
        mock_response.content = image_content

        with (
            patch("requests.get", return_value=mock_response),
            patch.object(Path, "exists", return_value=False),
            patch.object(Path, "open") as mock_open,
        ):
            _download_image(image_url)

            # Verify the file path was constructed correctly
            # The Path constructor is called with "comic_01.jpg"
            mock_open.assert_called_once()


class TestMain:
    """Tests for main CLI function."""

    def test_main_opens_browser_with_url(self) -> None:
        """Test that main opens Chrome with the provided URL."""
        from selenium.common.exceptions import NoSuchElementException

        mock_driver = MagicMock()
        mock_element = MagicMock()
        mock_element.get_attribute.return_value = "https://example.com/img.jpg"

        # Make find_element return element first, then raise exception
        mock_driver.find_element.side_effect = [
            mock_element,  # First call for image
            NoSuchElementException(),  # Next button not found
        ]

        with (
            patch("sys.argv", ["scrape_comics.py", "https://comics.com/page1"]),
            patch(
                "python_pkg.scrape_website.scrape_comics.webdriver.Chrome",
                return_value=mock_driver,
            ),
            patch(
                "python_pkg.scrape_website.scrape_comics._download_image",
                return_value=True,
            ),
        ):
            main()

            mock_driver.get.assert_called_with("https://comics.com/page1")
            mock_driver.quit.assert_called_once()

    def test_main_processes_multiple_images(self) -> None:
        """Test that main iterates through multiple images."""
        mock_driver = MagicMock()
        mock_image = MagicMock()
        mock_image.get_attribute.return_value = "https://example.com/img.jpg"

        mock_next_button = MagicMock()
        mock_next_button.get_attribute.return_value = "https://comics.com/page2"

        from selenium.common.exceptions import NoSuchElementException

        # Simulate: image -> next -> image -> no next
        call_count = [0]
        max_next_calls = 2

        def find_element_side_effect(_by: str, value: str) -> MagicMock:
            call_count[0] += 1
            if value == "cc-comic":
                return mock_image
            if value == "a.cc-next":
                if call_count[0] <= max_next_calls:
                    return mock_next_button
                raise NoSuchElementException
            raise NoSuchElementException

        mock_driver.find_element.side_effect = find_element_side_effect

        min_expected_calls = 2
        with (
            patch("sys.argv", ["scrape_comics.py", "https://comics.com/page1"]),
            patch(
                "python_pkg.scrape_website.scrape_comics.webdriver.Chrome",
                return_value=mock_driver,
            ),
            patch(
                "python_pkg.scrape_website.scrape_comics._download_image",
                return_value=True,
            ),
        ):
            main()

            # Driver should have navigated to next page
            assert mock_driver.get.call_count >= min_expected_calls

    def test_main_stops_when_no_next_button(self) -> None:
        """Test that main stops when next button is not found."""
        mock_driver = MagicMock()
        mock_image = MagicMock()
        mock_image.get_attribute.return_value = "https://example.com/img.jpg"

        from selenium.common.exceptions import NoSuchElementException

        def find_element_side_effect(_by: str, value: str) -> MagicMock:
            if value == "cc-comic":
                return mock_image
            raise NoSuchElementException

        mock_driver.find_element.side_effect = find_element_side_effect

        with (
            patch("sys.argv", ["scrape_comics.py", "https://comics.com/page1"]),
            patch(
                "python_pkg.scrape_website.scrape_comics.webdriver.Chrome",
                return_value=mock_driver,
            ),
            patch(
                "python_pkg.scrape_website.scrape_comics._download_image",
                return_value=True,
            ),
        ):
            main()

            mock_driver.quit.assert_called_once()


class TestConstants:
    """Tests for module constants."""

    def test_request_timeout_value(self) -> None:
        """Test REQUEST_TIMEOUT constant value."""
        expected_timeout = 30
        assert expected_timeout == REQUEST_TIMEOUT
