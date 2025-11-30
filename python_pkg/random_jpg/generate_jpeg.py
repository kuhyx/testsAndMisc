"""Generate random colorful JPEG images with configurable parameters."""

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import logging
from pathlib import Path
import secrets

from PIL import Image

_logger = logging.getLogger(__name__)

# Use cryptographically secure random number generator
_rng = secrets.SystemRandom()

MAX_IMAGE_SIZE = 1000


@dataclass
class ImageConfig:
    """Configuration for generating a bloated JPEG image."""

    size: int
    color_list: list[str]
    block_size: int
    output_path: str
    quality: int


def generate_bloated_jpeg(config: ImageConfig, image_index: int, folder: str) -> str:
    """Generates a random JPEG image with given configuration.

    Args:
        config: Image generation configuration.
        image_index: Index of the image for unique naming.
        folder: Folder to save the image.

    Returns:
        Path to the generated image.
    """
    # Ensure size is divisible by block_size and does not exceed MAX_IMAGE_SIZE
    if config.size > MAX_IMAGE_SIZE or config.size % config.block_size != 0:
        msg = (
            f"Size must be {MAX_IMAGE_SIZE} pixels or less and divisible by block_size"
        )
        raise ValueError(msg)

    # Create a new image
    image = Image.new("RGB", (config.size, config.size))
    pixels = image.load()

    # Convert hex colors to RGB
    rgb_colors = [
        tuple(int(color[i : i + 2], 16) for i in (1, 3, 5))
        for color in config.color_list
    ]

    # Fill the image with block_size x block_size pixel squares
    # of random colors from the list
    for y in range(0, config.size, config.block_size):
        for x in range(0, config.size, config.block_size):
            color = _rng.choice(rgb_colors)
            for i in range(config.block_size):
                for j in range(config.block_size):
                    pixels[x + i, y + j] = color

    # Create the folder if it does not exist
    folder_path = Path(folder)
    folder_path.mkdir(parents=True, exist_ok=True)

    # Generate unique output path
    output_stem = Path(config.output_path).stem
    output_suffix = Path(config.output_path).suffix
    unique_output_path = folder_path / f"{output_stem}_{image_index}{output_suffix}"

    # Save the image with specified quality to maximize file size
    image.save(unique_output_path, "JPEG", quality=config.quality, optimize=False)

    return str(unique_output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate bloated JPEG images with random colors."
    )
    parser.add_argument(
        "-n",
        "--num_images",
        type=int,
        default=1,
        help="Number of images to generate. Default is 1.",
    )
    parser.add_argument(
        "-s",
        "--size",
        type=int,
        default=1000,
        help=(
            "Size of the images (must be 1000 or less "
            "and divisible by block size). Default is 1000."
        ),
    )
    parser.add_argument(
        "-c",
        "--colors",
        nargs="+",
        default=["#FF5733", "#33FF57", "#3357FF", "#F3FF33", "#FF33F6", "#33FFF6"],
        help="List of colors in hex format. Uses 6 default colors if not specified.",
    )
    parser.add_argument(
        "-b",
        "--block_size",
        type=int,
        default=4,
        help=(
            "Size of the pixel blocks (must divide the "
            "image size evenly). Default is 4."
        ),
    )
    parser.add_argument(
        "-o",
        "--output_path",
        type=str,
        default="bloated_image.jpeg",
        help="Base output path for the JPEG images. Default is 'bloated_image.jpeg'.",
    )
    parser.add_argument(
        "-q",
        "--quality",
        type=int,
        default=100,
        help="Quality setting for the JPEG images (0-100). Default is 100.",
    )

    args = parser.parse_args()

    # Create folder named after the current timestamp
    timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
    folder = f"generated_images_{timestamp}"

    # Display used parameters
    _logger.info(
        "Generating %s image(s) with the following parameters:", args.num_images
    )
    _logger.info("  Size: %s", args.size)
    _logger.info("  Colors: %s", args.colors)
    _logger.info("  Block size: %s", args.block_size)
    _logger.info("  Base output path: %s", args.output_path)
    _logger.info("  Quality: %s", args.quality)
    _logger.info("  Output folder: %s", folder)

    # Generate the specified number of images
    config = ImageConfig(
        size=args.size,
        color_list=args.colors,
        block_size=args.block_size,
        output_path=args.output_path,
        quality=args.quality,
    )
    for i in range(1, args.num_images + 1):
        output_path = generate_bloated_jpeg(config, i, folder)
        _logger.info("Image %s saved to %s", i, Path(output_path).resolve())
