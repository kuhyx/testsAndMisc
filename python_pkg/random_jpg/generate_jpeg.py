"""Generate random colorful JPEG images with configurable parameters."""

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import logging
import os
import secrets

from PIL import Image

logging.basicConfig(level=logging.INFO)

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
    if not os.path.exists(folder):
        os.makedirs(folder)

    # Generate unique output path
    unique_output_path = os.path.join(
        folder,
        f"{os.path.splitext(config.output_path)[0]}_{image_index}"
        f"{os.path.splitext(config.output_path)[1]}",
    )

    # Save the image with specified quality to maximize file size
    image.save(unique_output_path, "JPEG", quality=config.quality, optimize=False)

    return unique_output_path


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
    logging.info(
        f"Generating {args.num_images} image(s) with the following parameters:"
    )
    logging.info(f"  Size: {args.size}")
    logging.info(f"  Colors: {args.colors}")
    logging.info(f"  Block size: {args.block_size}")
    logging.info(f"  Base output path: {args.output_path}")
    logging.info(f"  Quality: {args.quality}")
    logging.info(f"  Output folder: {folder}")

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
        logging.info(f"Image {i} saved to {os.path.abspath(output_path)}")
