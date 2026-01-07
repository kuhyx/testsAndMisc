#!/usr/bin/env python3
"""Anki flashcard generator for Warsaw districts.

Generates Anki-compatible flashcard decks with maps showing individual
Warsaw districts (dzielnice) with their borders.

Usage:
    # Generate Anki cards for all Warsaw districts
    python -m python_pkg.warsaw_districts.warsaw_districts_anki

    # Specify custom output file
    python -m python_pkg.warsaw_districts.warsaw_districts_anki --output warsaw.apkg

Output:
    Creates a self-contained .apkg file that can be directly imported into Anki.
    The file includes all images embedded, so no manual file copying is needed.
"""

from __future__ import annotations

import argparse
import hashlib
from io import BytesIO
from pathlib import Path
import random
import sys
from typing import TYPE_CHECKING, NamedTuple

import genanki
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


def generate_district_image_bytes(district: District) -> bytes:
    """Generate a district map image as bytes.

    Args:
        district: The district to visualize.

    Returns:
        PNG image data as bytes.
    """
    fig = create_district_map(district)

    # Save to bytes buffer
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=150)
    plt.close(fig)
    buf.seek(0)

    return buf.read()


def generate_anki_package(
    deck_name: str = "Warsaw Districts",
) -> genanki.Package:
    """Generate Anki package (.apkg) for Warsaw districts.

    Args:
        deck_name: Name for the Anki deck.

    Returns:
        genanki.Package object ready to be written to file.
    """
    # Create a unique model ID based on deck name
    model_id_hash = hashlib.md5(  # noqa: S324
        f"warsaw_districts_{deck_name}".encode()
    )
    model_id = int(model_id_hash.hexdigest()[:8], 16)

    # Define the note model (card template)
    my_model = genanki.Model(
        model_id,
        "Warsaw District Model",
        fields=[
            {"name": "DistrictMap"},
            {"name": "DistrictName"},
        ],
        templates=[
            {
                "name": "Card 1",
                "qfmt": "{{DistrictMap}}",
                "afmt": '{{FrontSide}}<hr id="answer">{{DistrictName}}',
            },
        ],
    )

    # Create a unique deck ID based on deck name
    deck_id = random.randrange(1 << 30, 1 << 31)  # noqa: S311

    # Create the deck
    my_deck = genanki.Deck(deck_id, deck_name)

    # Store media files
    media_files = []

    # Generate notes for each district
    for district in WARSAW_DISTRICTS:
        # Generate image
        image_data = generate_district_image_bytes(district)

        # Create unique filename
        filename = f"{district.name.replace('-', '_').replace(' ', '_')}.png"

        # Create note
        note = genanki.Note(
            model=my_model,
            fields=[
                f'<img src="{filename}">',
                district.name,
            ],
            tags=["geography", "warsaw", "poland"],
        )

        my_deck.add_note(note)

        # Save image data to temporary file for packaging
        temp_path = Path(f"/tmp/{filename}")  # noqa: S108
        temp_path.write_bytes(image_data)
        media_files.append(str(temp_path))

    # Create package
    package = genanki.Package(my_deck)
    package.media_files = media_files

    return package


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
        help="Output file path (default: warsaw_districts.apkg)",
    )
    parser.add_argument(
        "--deck-name",
        "-d",
        type=str,
        default="Warsaw Districts",
        help="Name for the Anki deck (default: 'Warsaw Districts')",
    )

    args = parser.parse_args(argv)

    # Determine output path
    output_path = (
        Path(args.output) if args.output else Path("warsaw_districts.apkg")
    )

    try:
        num_districts = len(WARSAW_DISTRICTS)
        sys.stdout.write(
            f"Generating flashcards for {num_districts} Warsaw districts...\n"
        )

        # Generate the package
        package = generate_anki_package(args.deck_name)

        # Write to file
        package.write_to_file(str(output_path))

        sys.stdout.write("\n")
        sys.stdout.write("=" * 60 + "\n")
        sys.stdout.write("FLASHCARD GENERATION COMPLETE\n")
        sys.stdout.write("=" * 60 + "\n")
        sys.stdout.write(f"Districts: {num_districts}\n")
        sys.stdout.write(f"Output file: {output_path.absolute()}\n")
        sys.stdout.write("\n")
        sys.stdout.write("To import into Anki:\n")
        sys.stdout.write("  1. Open Anki\n")
        sys.stdout.write("  2. File -> Import\n")
        sys.stdout.write(f"  3. Select: {output_path.absolute()}\n")
        sys.stdout.write("  4. Click Import\n")
        sys.stdout.write("\n")
        sys.stdout.write("All images are embedded in the .apkg file!\n")
    except (OSError, ValueError) as e:
        sys.stderr.write(f"Error: {e}\n")
        return 1
    else:
        return 0


if __name__ == "__main__":
    sys.exit(main())
