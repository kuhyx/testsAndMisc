#!/usr/bin/env python3
"""Anki flashcard generator for Warsaw districts.

Generates Anki-compatible flashcard decks with maps showing individual
Warsaw districts (dzielnice) with their borders using real boundary data
from OpenStreetMap.

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
from typing import TYPE_CHECKING

import genanki
import geopandas as gpd
import matplotlib.pyplot as plt

if TYPE_CHECKING:
    from collections.abc import Sequence

    from matplotlib.figure import Figure


# Path to GeoJSON file with Warsaw district boundaries
GEOJSON_PATH = Path(__file__).parent / "warszawa-dzielnice.geojson"


def load_district_data() -> gpd.GeoDataFrame:
    """Load Warsaw district boundaries from GeoJSON.

    Returns:
        GeoDataFrame with district boundaries.
    """
    if not GEOJSON_PATH.exists():
        msg = f"GeoJSON file not found at {GEOJSON_PATH}"
        raise FileNotFoundError(msg)

    gdf = gpd.read_file(GEOJSON_PATH)
    # Filter out the "Warszawa" entry (whole city) and keep only districts
    return gdf[gdf["name"] != "Warszawa"].copy()


def get_district_names() -> list[str]:
    """Get list of all district names from GeoJSON data.

    Returns:
        Sorted list of district names.
    """
    gdf = load_district_data()
    return sorted(gdf["name"].tolist())


# Load district names from actual data
WARSAW_DISTRICTS = get_district_names()


def create_district_map(district_name: str) -> Figure:
    """Create a map showing Warsaw districts with one district highlighted.

    Args:
        district_name: Name of the district to highlight.

    Returns:
        A matplotlib Figure object.
    """
    # Load all district data
    gdf = load_district_data()

    # Create figure
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.set_aspect("equal")
    ax.axis("off")

    # Plot all districts with light gray borders
    gdf.boundary.plot(ax=ax, color="lightgray", linewidth=0.5, alpha=0.5)

    # Find and highlight the target district
    target = gdf[gdf["name"] == district_name]
    if len(target) == 0:
        msg = f"District {district_name} not found in data"
        raise ValueError(msg)

    # Plot the highlighted district with bold black border
    target.boundary.plot(ax=ax, color="black", linewidth=3)

    # Set tight layout
    ax.set_xlim(gdf.total_bounds[0], gdf.total_bounds[2])
    ax.set_ylim(gdf.total_bounds[1], gdf.total_bounds[3])

    return fig


def generate_district_image_bytes(district_name: str) -> bytes:
    """Generate a district map image as bytes.

    Args:
        district_name: Name of the district to visualize.

    Returns:
        PNG image data as bytes.
    """
    fig = create_district_map(district_name)

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
    for district_name in WARSAW_DISTRICTS:
        # Generate image
        image_data = generate_district_image_bytes(district_name)

        # Create unique filename
        filename = f"{district_name.replace(' ', '_').replace('-', '_')}.png"

        # Create note
        note = genanki.Note(
            model=my_model,
            fields=[
                f'<img src="{filename}">',
                district_name,
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
        sys.stdout.write("Using real district boundaries from OpenStreetMap data.\n")

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
