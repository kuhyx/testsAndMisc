import argparse
from datetime import datetime
import os
import random

from PIL import Image


def generate_bloated_jpeg(
    size, color_list, block_size, output_path, quality, image_index, folder
):
    """Generates a random JPEG image with given size, list of colors, and block size.

    Args:
    size (int): Size of the image (both width and height, must be divisible by block_size).
    color_list (list of str): List of colors in hex format.
    block_size (int): Size of the pixel blocks.
    output_path (str): Output path for the JPEG image.
    quality (int): Quality setting for the JPEG image (0-100).
    image_index (int): Index of the image for unique naming.
    folder (str): Folder to save the image.
    """
    # Ensure size is divisible by block_size and does not exceed 1000 pixels
    if size > 1000 or size % block_size != 0:
        raise ValueError("Size must be 1000 pixels or less and divisible by block_size")

    # Create a new image
    image = Image.new("RGB", (size, size))
    pixels = image.load()

    # Convert hex colors to RGB
    rgb_colors = [
        tuple(int(color[i : i + 2], 16) for i in (1, 3, 5)) for color in color_list
    ]

    # Fill the image with block_size x block_size pixel squares of random colors from the list
    for y in range(0, size, block_size):
        for x in range(0, size, block_size):
            color = random.choice(rgb_colors)
            for i in range(block_size):
                for j in range(block_size):
                    pixels[x + i, y + j] = color

    # Create the folder if it does not exist
    if not os.path.exists(folder):
        os.makedirs(folder)

    # Generate unique output path
    unique_output_path = os.path.join(
        folder,
        f"{os.path.splitext(output_path)[0]}_{image_index}{os.path.splitext(output_path)[1]}",
    )

    # Save the image with specified quality to maximize file size
    image.save(unique_output_path, "JPEG", quality=quality, optimize=False)

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
        help="Size of the images (must be 1000 or less and divisible by block size). Default is 1000.",
    )
    parser.add_argument(
        "-c",
        "--colors",
        nargs="+",
        default=["#FF5733", "#33FF57", "#3357FF", "#F3FF33", "#FF33F6", "#33FFF6"],
        help="List of colors in hex format. Default is ['#FF5733', '#33FF57', '#3357FF', '#F3FF33', '#FF33F6', '#33FFF6'].",
    )
    parser.add_argument(
        "-b",
        "--block_size",
        type=int,
        default=4,
        help="Size of the pixel blocks (must divide the image size evenly). Default is 4.",
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
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = f"generated_images_{timestamp}"

    # Display used parameters
    print(f"Generating {args.num_images} image(s) with the following parameters:")
    print(f"  Size: {args.size}")
    print(f"  Colors: {args.colors}")
    print(f"  Block size: {args.block_size}")
    print(f"  Base output path: {args.output_path}")
    print(f"  Quality: {args.quality}")
    print(f"  Output folder: {folder}")

    # Generate the specified number of images
    for i in range(1, args.num_images + 1):
        output_path = generate_bloated_jpeg(
            args.size,
            args.colors,
            args.block_size,
            args.output_path,
            args.quality,
            i,
            folder,
        )
        print(f"Image {i} saved to {os.path.abspath(output_path)}")
