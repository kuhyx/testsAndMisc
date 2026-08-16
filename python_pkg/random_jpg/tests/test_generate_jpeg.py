"""Unit tests for generate_jpeg module."""

from pathlib import Path
import tempfile

from PIL import Image
import pytest

from python_pkg.random_jpg.generate_jpeg import (
    MAX_IMAGE_SIZE,
    ImageConfig,
    _create_random_image,
    generate_bloated_jpeg,
)


class TestImageConfig:
    """Tests for ImageConfig dataclass."""

    def test_creates_config_with_all_fields(self) -> None:
        """Test ImageConfig stores all configuration fields."""
        config = ImageConfig(
            size=100,
            color_list=["#FF0000", "#00FF00"],
            block_size=10,
            output_path="test.jpeg",
            quality=95,
        )
        assert config.size == 100
        assert config.color_list == ["#FF0000", "#00FF00"]
        assert config.block_size == 10
        assert config.output_path == "test.jpeg"
        assert config.quality == 95


class TestGenerateBloatedJpeg:
    """Tests for generate_bloated_jpeg function."""

    def test_generates_image_file(self) -> None:
        """Test that generate_bloated_jpeg creates an image file."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = ImageConfig(
                size=100,
                color_list=["#FF0000", "#00FF00", "#0000FF"],
                block_size=10,
                output_path="test.jpeg",
                quality=90,
            )
            result_path = generate_bloated_jpeg(config, 1, tmp_dir)

            assert Path(result_path).exists()
            # Verify it's a valid image
            with Image.open(result_path) as img:
                assert img.size == (100, 100)

    def test_raises_error_for_size_exceeding_max(self) -> None:
        """Test ValueError when size exceeds MAX_IMAGE_SIZE."""
        config = ImageConfig(
            size=MAX_IMAGE_SIZE + 1,
            color_list=["#FF0000"],
            block_size=10,
            output_path="test.jpeg",
            quality=90,
        )
        with (
            tempfile.TemporaryDirectory() as tmp_dir,
            pytest.raises(ValueError, match="1000 pixels or less"),
        ):
            generate_bloated_jpeg(config, 1, tmp_dir)

    def test_raises_error_for_indivisible_size(self) -> None:
        """Test ValueError when size not divisible by block_size."""
        config = ImageConfig(
            size=100,
            color_list=["#FF0000"],
            block_size=7,  # 100 is not divisible by 7
            output_path="test.jpeg",
            quality=90,
        )
        with (
            tempfile.TemporaryDirectory() as tmp_dir,
            pytest.raises(ValueError, match="divisible by block_size"),
        ):
            generate_bloated_jpeg(config, 1, tmp_dir)

    def test_unique_naming_with_index(self) -> None:
        """Test that images are named with index."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = ImageConfig(
                size=100,
                color_list=["#FF0000"],
                block_size=10,
                output_path="output.jpeg",
                quality=90,
            )
            path1 = generate_bloated_jpeg(config, 1, tmp_dir)
            path2 = generate_bloated_jpeg(config, 2, tmp_dir)

            assert "output_1.jpeg" in path1
            assert "output_2.jpeg" in path2


class TestCreateRandomImage:
    """Tests for _create_random_image function."""

    def test_creates_image_with_correct_size(self) -> None:
        """Test created image has correct dimensions."""
        config = ImageConfig(
            size=100,
            color_list=["#FF0000", "#00FF00"],
            block_size=10,
            output_path="test.jpeg",
            quality=90,
        )
        image = _create_random_image(config)

        assert image.size == (100, 100)
        assert image.mode == "RGB"

    def test_fills_image_with_blocks(self) -> None:
        """Test image is filled with colored blocks."""
        config = ImageConfig(
            size=20,
            color_list=["#FF0000"],  # Only red
            block_size=10,
            output_path="test.jpeg",
            quality=90,
        )
        image = _create_random_image(config)
        pixels = image.load()

        # With only red color, all pixels should be red
        for x in range(20):
            for y in range(20):
                assert pixels[x, y] == (255, 0, 0)
