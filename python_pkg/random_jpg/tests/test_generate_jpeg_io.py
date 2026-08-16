"""Tests for saving generated images and the CLI entry point."""

from pathlib import Path
import tempfile
from unittest.mock import patch

from PIL import Image

from python_pkg.random_jpg.generate_jpeg import (
    MAX_IMAGE_SIZE,
    ImageConfig,
    _save_image,
    main,
)


class TestSaveImage:
    """Tests for _save_image function."""

    def test_creates_output_folder(self) -> None:
        """Test that output folder is created if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            new_folder = Path(tmp_dir) / "new_subfolder"
            image = Image.new("RGB", (10, 10))
            config = ImageConfig(
                size=10,
                color_list=["#FF0000"],
                block_size=10,
                output_path="image.jpeg",
                quality=90,
            )

            _save_image(image, config, 1, str(new_folder))

            assert new_folder.exists()

    def test_saves_with_correct_quality(self) -> None:
        """Test image is saved with specified quality."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            image = Image.new("RGB", (10, 10), color=(255, 0, 0))
            config = ImageConfig(
                size=10,
                color_list=["#FF0000"],
                block_size=10,
                output_path="image.jpeg",
                quality=50,
            )

            result_path = _save_image(image, config, 1, tmp_dir)

            assert Path(result_path).exists()


class TestMain:
    """Tests for main CLI function."""

    def test_main_generates_image_with_defaults(self) -> None:
        """Test main generates image with default arguments."""
        with (
            tempfile.TemporaryDirectory() as tmp_dir,
            patch("sys.argv", ["generate_jpeg.py"]),
            patch(
                "python_pkg.random_jpg.generate_jpeg.generate_bloated_jpeg"
            ) as mock_gen,
        ):
            mock_gen.return_value = f"{tmp_dir}/test.jpeg"
            main()

            mock_gen.assert_called_once()
            call_args = mock_gen.call_args
            config = call_args[0][0]
            assert config.size == 1000
            assert config.block_size == 4
            assert config.quality == 100

    def test_main_respects_num_images_argument(self) -> None:
        """Test main generates multiple images when specified."""
        with (
            tempfile.TemporaryDirectory() as tmp_dir,
            patch("sys.argv", ["generate_jpeg.py", "-n", "3"]),
            patch(
                "python_pkg.random_jpg.generate_jpeg.generate_bloated_jpeg"
            ) as mock_gen,
        ):
            mock_gen.return_value = f"{tmp_dir}/test.jpeg"
            main()

            assert mock_gen.call_count == 3

    def test_main_uses_custom_size(self) -> None:
        """Test main respects custom size argument."""
        with (
            tempfile.TemporaryDirectory() as tmp_dir,
            patch("sys.argv", ["generate_jpeg.py", "-s", "500", "-b", "5"]),
            patch(
                "python_pkg.random_jpg.generate_jpeg.generate_bloated_jpeg"
            ) as mock_gen,
        ):
            mock_gen.return_value = f"{tmp_dir}/test.jpeg"
            main()

            config = mock_gen.call_args[0][0]
            assert config.size == 500
            assert config.block_size == 5

    def test_main_uses_custom_colors(self) -> None:
        """Test main respects custom color list."""
        with (
            tempfile.TemporaryDirectory() as tmp_dir,
            patch("sys.argv", ["generate_jpeg.py", "-c", "#AABBCC", "#112233"]),
            patch(
                "python_pkg.random_jpg.generate_jpeg.generate_bloated_jpeg"
            ) as mock_gen,
        ):
            mock_gen.return_value = f"{tmp_dir}/test.jpeg"
            main()

            config = mock_gen.call_args[0][0]
            assert config.color_list == ["#AABBCC", "#112233"]


class TestConstants:
    """Tests for module constants."""

    def test_max_image_size(self) -> None:
        """Test MAX_IMAGE_SIZE constant value."""
        assert MAX_IMAGE_SIZE == 1000
