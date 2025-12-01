"""Unit tests for tag_divider module constants.

Note: The tag_divider module runs interactive code at import time,
making it difficult to test the main functionality without refactoring.
These tests verify the module-level constants.
"""

from unittest.mock import patch


class TestImageExtensionConstant:
    """Tests for IMAGE_EXTENSION constant."""

    def test_contains_common_formats(self) -> None:
        """Test IMAGE_EXTENSION includes common image formats."""
        # Import in test to avoid triggering the interactive code
        with (
            patch("builtins.input", side_effect=["folder_a", "folder_d"]),
            patch("pathlib.Path.is_dir", return_value=True),
            patch("pathlib.Path.iterdir", return_value=[]),
        ):
            from python_pkg.tag_divider.tag_divider import IMAGE_EXTENSION

        assert ".jpg" in IMAGE_EXTENSION
        assert ".jpeg" in IMAGE_EXTENSION
        assert ".png" in IMAGE_EXTENSION
        assert ".bmp" in IMAGE_EXTENSION
        assert ".tiff" in IMAGE_EXTENSION

    def test_is_tuple(self) -> None:
        """Test IMAGE_EXTENSION is a tuple."""
        with (
            patch("builtins.input", side_effect=["folder_a", "folder_d"]),
            patch("pathlib.Path.is_dir", return_value=True),
            patch("pathlib.Path.iterdir", return_value=[]),
        ):
            from python_pkg.tag_divider.tag_divider import IMAGE_EXTENSION

        assert isinstance(IMAGE_EXTENSION, tuple)


class TestKeyCodeConstants:
    """Tests for keyboard code constants."""

    def test_left_folder_code_is_d(self) -> None:
        """Test LEFT_FOLDER_CODE is 'd' (100)."""
        with (
            patch("builtins.input", side_effect=["folder_a", "folder_d"]),
            patch("pathlib.Path.is_dir", return_value=True),
            patch("pathlib.Path.iterdir", return_value=[]),
        ):
            from python_pkg.tag_divider.tag_divider import LEFT_FOLDER_CODE

        expected_code = 100  # ASCII code for 'd'
        assert expected_code == LEFT_FOLDER_CODE

    def test_right_folder_code_is_a(self) -> None:
        """Test RIGHT_FOLDER_CODE is 'a' (97)."""
        with (
            patch("builtins.input", side_effect=["folder_a", "folder_d"]),
            patch("pathlib.Path.is_dir", return_value=True),
            patch("pathlib.Path.iterdir", return_value=[]),
        ):
            from python_pkg.tag_divider.tag_divider import RIGHT_FOLDER_CODE

        expected_code = 97  # ASCII code for 'a'
        assert expected_code == RIGHT_FOLDER_CODE
