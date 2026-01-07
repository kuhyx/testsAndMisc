#!/usr/bin/env python3
"""Anki flashcard generator for Warsaw districts.

Generates Anki-compatible flashcard decks with maps showing individual
Warsaw districts (dzielnice) with their borders.

Usage:
    # Generate Anki cards for all Warsaw districts
    python -m python_pkg.warsaw_districts.warsaw_districts_anki

    # Specify custom output file
    python -m python_pkg.warsaw_districts.warsaw_districts_anki --output warsaw.txt

    # Specify custom output directory for images
    python -m python_pkg.warsaw_districts.warsaw_districts_anki --image-dir ./maps

Output:
    Creates a semicolon-separated text file that can be imported into Anki.
    Format: <img src="district_name.png">;district_name_in_polish
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import TYPE_CHECKING, NamedTuple

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt

if TYPE_CHECKING:
    from collections.abc import Sequence

    from matplotlib.figure import Figure


class District(NamedTuple):
    """A Warsaw district with its approximate position."""

    name: str  # Polish name
    x: float  # Approximate x coordinate (0-1)
    y: float  # Approximate y coordinate (0-1)


# Warsaw districts (dzielnice) - 18 total
# Coordinates are approximate relative positions for visualization
WARSAW_DISTRICTS: list[District] = [
    District("Bemowo", 0.15, 0.55),
    District("Białołęka", 0.75, 0.7),
    District("Bielany", 0.35, 0.75),
    District("Mokotów", 0.45, 0.3),
    District("Ochota", 0.3, 0.45),
    District("Praga-Południe", 0.7, 0.35),
    District("Praga-Północ", 0.7, 0.6),
    District("Rembertów", 0.85, 0.5),
    District("Śródmieście", 0.5, 0.5),
    District("Targówek", 0.65, 0.8),
    District("Ursus", 0.05, 0.4),
    District("Ursynów", 0.5, 0.15),
    District("Wawer", 0.8, 0.25),
    District("Wesoła", 0.9, 0.45),
    District("Wilanów", 0.6, 0.1),
    District("Włochy", 0.15, 0.3),
    District("Wola", 0.35, 0.6),
    District("Żoliborz", 0.45, 0.7),
]


def create_district_map(district: District, *, highlight_only: bool = True) -> Figure:
    """Create a map showing Warsaw districts with one district highlighted.

    Args:
        district: The district to highlight.
        highlight_only: If True, show only the highlighted district's border.

    Returns:
        A matplotlib Figure object.
    """
    fig, ax = plt.subplots(figsize=(8, 8))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_aspect("equal")
    ax.axis("off")

    # Draw all districts as points if not highlight_only
    if not highlight_only:
        for dist in WARSAW_DISTRICTS:
            if dist.name != district.name:
                circle = mpatches.Circle(
                    (dist.x, dist.y),
                    0.03,
                    color="lightgray",
                    alpha=0.3,
                )
                ax.add_patch(circle)

    # Draw the highlighted district with a border
    # Create a polygon approximating the district area
    # For simplicity, we'll use a circle with border
    highlighted = mpatches.Circle(
        (district.x, district.y),
        0.08,
        facecolor="white",
        edgecolor="black",
        linewidth=3,
    )
    ax.add_patch(highlighted)

    # Add some neighboring circles to show context (lighter borders)
    # Find nearest districts
    distances = [
        (
            d,
            ((d.x - district.x) ** 2 + (d.y - district.y) ** 2) ** 0.5,
        )
        for d in WARSAW_DISTRICTS
        if d.name != district.name
    ]
    distances.sort(key=lambda x: x[1])

    # Draw 3-4 nearest neighbors with light borders
    for neighbor, _ in distances[:4]:
        neighbor_circle = mpatches.Circle(
            (neighbor.x, neighbor.y),
            0.08,
            facecolor="white",
            edgecolor="lightgray",
            linewidth=1,
            alpha=0.5,
        )
        ax.add_patch(neighbor_circle)

    return fig


def save_district_image(district: District, output_dir: Path) -> Path:
    """Save a district map image to a file.

    Args:
        district: The district to visualize.
        output_dir: Directory to save the image.

    Returns:
        Path to the saved image file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    fig = create_district_map(district)

    # Create filename from district name (sanitized)
    filename = f"{district.name.replace('-', '_').replace(' ', '_')}.png"
    output_path = output_dir / filename

    fig.savefig(output_path, format="png", bbox_inches="tight", dpi=150)
    plt.close(fig)

    return output_path


def generate_anki_deck(
    output_dir: Path,
    deck_name: str = "Warsaw Districts",
) -> str:
    """Generate Anki-compatible deck content for Warsaw districts.

    Args:
        output_dir: Directory where images will be saved.
        deck_name: Name for the Anki deck.

    Returns:
        Semicolon-separated content ready for Anki import.
    """
    lines: list[str] = []

    # Add Anki headers
    lines.append("#separator:semicolon")
    lines.append("#html:true")
    lines.append(f"#deck:{deck_name}")
    lines.append("#tags:geography warsaw poland")
    lines.append("#columns:Front;Back")
    lines.append("")  # Empty line before data

    # Generate cards for each district
    for district in WARSAW_DISTRICTS:
        # Save the image
        image_path = save_district_image(district, output_dir)

        # Create the front side: reference to image
        # Anki expects the image filename to be in the media collection
        front = f'<img src="{image_path.name}">'

        # Back side: district name in Polish
        back = district.name

        lines.append(f"{front};{back}")

    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    """Main entry point.

    Args:
        argv: Command line arguments.

    Returns:
        Exit code.
    """
    parser = argparse.ArgumentParser(
        description="Generate Anki flashcards for Warsaw districts.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Output file path (default: warsaw_districts_anki.txt)",
    )
    parser.add_argument(
        "--image-dir",
        "-i",
        type=str,
        default=None,
        help="Directory for district images (default: warsaw_districts_images)",
    )
    parser.add_argument(
        "--deck-name",
        "-d",
        type=str,
        default="Warsaw Districts",
        help="Name for the Anki deck (default: 'Warsaw Districts')",
    )

    args = parser.parse_args(argv)

    # Determine output paths
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = Path("warsaw_districts_anki.txt")

    if args.image_dir:
        image_dir = Path(args.image_dir)
    else:
        image_dir = Path("warsaw_districts_images")

    try:
        print(f"Generating flashcards for {len(WARSAW_DISTRICTS)} Warsaw districts...")  # noqa: T201

        # Generate the deck content
        anki_content = generate_anki_deck(image_dir, args.deck_name)

        # Write output file
        output_path.write_text(anki_content, encoding="utf-8")

        print()  # noqa: T201
        print("=" * 60)  # noqa: T201
        print("FLASHCARD GENERATION COMPLETE")  # noqa: T201
        print("=" * 60)  # noqa: T201
        print(f"Districts: {len(WARSAW_DISTRICTS)}")  # noqa: T201
        print(f"Images directory: {image_dir.absolute()}")  # noqa: T201
        print(f"Output file: {output_path.absolute()}")  # noqa: T201
        print()  # noqa: T201
        print("To import into Anki:")  # noqa: T201
        print("  1. Open Anki")  # noqa: T201
        print("  2. File -> Import")  # noqa: T201
        print(f"  3. Select: {output_path.absolute()}")  # noqa: T201
        img_dir = image_dir.absolute()
        print(f"  4. Ensure images from {img_dir} are in Anki's media folder")  # noqa: T201
        print("     or copy them to your Anki profile's collection.media folder")  # noqa: T201
        print("  5. Click Import")  # noqa: T201
    except Exception as e:  # noqa: BLE001
        print(f"Error: {e}", file=sys.stderr)  # noqa: T201
        return 1
    else:
        return 0


if __name__ == "__main__":
    sys.exit(main())
