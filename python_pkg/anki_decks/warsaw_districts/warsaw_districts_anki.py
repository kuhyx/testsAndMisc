#!/usr/bin/env python3
"""Anki flashcard generator for Warsaw districts.

Generates Anki-compatible flashcard decks with maps showing individual
Warsaw districts (dzielnice) with their borders using real boundary data
from OpenStreetMap.

Usage:
    # Generate Anki cards for all Warsaw districts
    python -m python_pkg.anki_decks.warsaw_districts.warsaw_districts_anki

    # Specify custom output file
    python -m python_pkg.anki_decks.warsaw_districts.warsaw_districts_anki \
        --output warsaw.apkg

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


# 18 unique distinct colors for all Warsaw districts
# Chosen to be visually distinct from each other in both light and dark modes
DISTRICT_COLORS = [
    "#E74C3C",  # Red
    "#3498DB",  # Blue
    "#2ECC71",  # Emerald green
    "#9B59B6",  # Purple
    "#F39C12",  # Orange
    "#1ABC9C",  # Turquoise
    "#E91E63",  # Pink
    "#00BCD4",  # Cyan
    "#8BC34A",  # Light green
    "#FF5722",  # Deep orange
    "#673AB7",  # Deep purple
    "#FFEB3B",  # Yellow
    "#795548",  # Brown
    "#607D8B",  # Blue grey
    "#CDDC39",  # Lime
    "#FF9800",  # Amber
    "#4CAF50",  # Green
    "#03A9F4",  # Light blue
]


def create_district_map(district_name: str) -> Figure:
    """Create a map showing Warsaw with one district highlighted.

    The map shows Warsaw as a plain shape (no internal district borders)
    with only the target district highlighted in color with a bold border.
    This makes it harder to guess the district using contextual cues.

    Args:
        district_name: Name of the district to highlight.

    Returns:
        A matplotlib Figure object.
    """
    # Load all district data
    gdf = load_district_data()

    # Create figure with transparent background
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_alpha(0)
    ax.patch.set_alpha(0)

    # Find the target district
    target = gdf[gdf["name"] == district_name]
    if len(target) == 0:
        msg = f"District {district_name} not found in data"
        raise ValueError(msg)

    # Create unified Warsaw shape by dissolving all districts
    warsaw_unified = gdf.union_all()

    # Plot Warsaw as a plain gray shape (no internal borders)
    warsaw_gdf = gpd.GeoDataFrame(geometry=[warsaw_unified], crs=gdf.crs)
    warsaw_gdf.plot(ax=ax, color="#D5D8DC", alpha=0.6)
    warsaw_gdf.boundary.plot(ax=ax, color="#2C3E50", linewidth=2)

    # Assign colors to districts based on sorted names for consistency
    sorted_names = sorted(gdf["name"].tolist())
    color_map = {
        name: DISTRICT_COLORS[i % len(DISTRICT_COLORS)]
        for i, name in enumerate(sorted_names)
    }

    # Highlight only the target district with bright color and bold border
    fill_color = color_map[district_name]
    target.plot(ax=ax, color=fill_color, alpha=0.9)
    target.boundary.plot(ax=ax, color="#1A1A1A", linewidth=4)

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

    # Define the note model (card template) with centered styling
    card_css = """
.card {
    font-family: Arial, sans-serif;
    font-size: 24px;
    text-align: center;
    color: #333;
    background-color: #fff;
}
.card.night_mode {
    color: #eee;
    background-color: #2f2f2f;
}
.map-container {
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 80vh;
}
.map-container img {
    max-width: 100%;
    max-height: 80vh;
    object-fit: contain;
}
.answer-text {
    font-size: 32px;
    font-weight: bold;
    margin-top: 20px;
    color: #2C3E50;
}
.card.night_mode .answer-text {
    color: #ECF0F1;
}
"""

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
                "qfmt": '<div class="map-container">{{DistrictMap}}</div>',
                "afmt": '<div class="map-container">{{DistrictMap}}</div>'
                '<hr id="answer">'
                '<div class="answer-text">{{DistrictName}}</div>',
            },
        ],
        css=card_css,
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
    output_path = Path(args.output) if args.output else Path("warsaw_districts.apkg")

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
