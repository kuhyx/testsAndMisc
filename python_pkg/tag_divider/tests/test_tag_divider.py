"""Unit tests for tag_divider module constants.

Note: The tag_divider module runs interactive code at import time,
making it difficult to test the main functionality without refactoring.
These tests verify the module-level constants.
"""

from pathlib import Path
import sys
from unittest.mock import MagicMock, patch


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


class TestModuleExecution:
    """Tests for module-level execution code."""

    def test_creates_folders_when_not_exist(self) -> None:
        """Test that folders are created when they don't exist."""
        # Unload module if already imported
        if "python_pkg.tag_divider.tag_divider" in sys.modules:
            del sys.modules["python_pkg.tag_divider.tag_divider"]

        mock_mkdir = MagicMock()
        is_dir_results = [False, False]  # Both folders don't exist

        with (
            patch("builtins.input", side_effect=["new_folder_a", "new_folder_d"]),
            patch("pathlib.Path.is_dir", side_effect=is_dir_results),
            patch("pathlib.Path.mkdir", mock_mkdir),
            patch("pathlib.Path.iterdir", return_value=[]),
            patch("os.chdir"),
        ):
            import python_pkg.tag_divider.tag_divider  # noqa: F401

        # mkdir should have been called twice (once for each folder)
        assert mock_mkdir.call_count == 2

    def test_skips_folder_creation_when_exist(self) -> None:
        """Test that folders are not created when they already exist."""
        # Unload module if already imported
        if "python_pkg.tag_divider.tag_divider" in sys.modules:
            del sys.modules["python_pkg.tag_divider.tag_divider"]

        mock_mkdir = MagicMock()

        with (
            patch("builtins.input", side_effect=["existing_a", "existing_d"]),
            patch("pathlib.Path.is_dir", return_value=True),  # Both exist
            patch("pathlib.Path.mkdir", mock_mkdir),
            patch("pathlib.Path.iterdir", return_value=[]),
            patch("os.chdir"),
        ):
            import python_pkg.tag_divider.tag_divider  # noqa: F401

        # mkdir should not have been called
        mock_mkdir.assert_not_called()

    def test_processes_image_with_right_key(self) -> None:
        """Test processing image and moving to first folder with 'a' key."""
        # Unload module if already imported
        if "python_pkg.tag_divider.tag_divider" in sys.modules:
            del sys.modules["python_pkg.tag_divider.tag_divider"]

        # Create mock file path
        mock_file = MagicMock(spec=Path)
        mock_file.name = "test_image.jpg"

        mock_cv2 = MagicMock()
        mock_cv2.IMREAD_COLOR = 1
        mock_cv2.waitKey.return_value = 97  # 'a' key - RIGHT_FOLDER_CODE

        mock_move = MagicMock()

        with (
            patch("builtins.input", side_effect=["folder_a", "folder_d"]),
            patch("pathlib.Path.is_dir", return_value=True),
            patch("pathlib.Path.iterdir", return_value=[mock_file]),
            patch("os.chdir"),
            patch.dict("sys.modules", {"cv2": mock_cv2}),
            patch("shutil.move", mock_move),
        ):
            import python_pkg.tag_divider.tag_divider  # noqa: F401

        # Image should be moved to first folder
        mock_move.assert_called_once()

    def test_processes_image_with_left_key(self) -> None:
        """Test processing image and moving to second folder with 'd' key."""
        # Unload module if already imported
        if "python_pkg.tag_divider.tag_divider" in sys.modules:
            del sys.modules["python_pkg.tag_divider.tag_divider"]

        # Create mock file path
        mock_file = MagicMock(spec=Path)
        mock_file.name = "test_image.png"

        mock_cv2 = MagicMock()
        mock_cv2.IMREAD_COLOR = 1
        mock_cv2.waitKey.return_value = 100  # 'd' key - LEFT_FOLDER_CODE

        mock_move = MagicMock()

        with (
            patch("builtins.input", side_effect=["folder_a", "folder_d"]),
            patch("pathlib.Path.is_dir", return_value=True),
            patch("pathlib.Path.iterdir", return_value=[mock_file]),
            patch("os.chdir"),
            patch.dict("sys.modules", {"cv2": mock_cv2}),
            patch("shutil.move", mock_move),
        ):
            import python_pkg.tag_divider.tag_divider  # noqa: F401

        # Image should be moved to second folder
        mock_move.assert_called_once()

    def test_skips_non_image_files(self) -> None:
        """Test that non-image files are skipped."""
        # Unload module if already imported
        if "python_pkg.tag_divider.tag_divider" in sys.modules:
            del sys.modules["python_pkg.tag_divider.tag_divider"]

        # Create mock file path for non-image
        mock_file = MagicMock(spec=Path)
        mock_file.name = "document.txt"

        mock_cv2 = MagicMock()
        mock_move = MagicMock()

        with (
            patch("builtins.input", side_effect=["folder_a", "folder_d"]),
            patch("pathlib.Path.is_dir", return_value=True),
            patch("pathlib.Path.iterdir", return_value=[mock_file]),
            patch("os.chdir"),
            patch.dict("sys.modules", {"cv2": mock_cv2}),
            patch("shutil.move", mock_move),
        ):
            import python_pkg.tag_divider.tag_divider  # noqa: F401

        # No image processing should have occurred
        mock_cv2.imread.assert_not_called()
        mock_move.assert_not_called()

    def test_ignores_other_key_presses(self) -> None:
        """Test that other key presses don't move the file."""
        # Unload module if already imported
        if "python_pkg.tag_divider.tag_divider" in sys.modules:
            del sys.modules["python_pkg.tag_divider.tag_divider"]

        # Create mock file path
        mock_file = MagicMock(spec=Path)
        mock_file.name = "test_image.jpg"

        mock_cv2 = MagicMock()
        mock_cv2.IMREAD_COLOR = 1
        mock_cv2.waitKey.return_value = 27  # ESC key - not 'a' or 'd'

        mock_move = MagicMock()

        with (
            patch("builtins.input", side_effect=["folder_a", "folder_d"]),
            patch("pathlib.Path.is_dir", return_value=True),
            patch("pathlib.Path.iterdir", return_value=[mock_file]),
            patch("os.chdir"),
            patch.dict("sys.modules", {"cv2": mock_cv2}),
            patch("shutil.move", mock_move),
        ):
            import python_pkg.tag_divider.tag_divider  # noqa: F401

        # File should not be moved
        mock_move.assert_not_called()
