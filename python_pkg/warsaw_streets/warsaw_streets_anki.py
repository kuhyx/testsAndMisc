#!/usr/bin/env python3
"""Anki flashcard generator for Warsaw streets.

Generates Anki-compatible flashcard decks with maps showing individual
Warsaw streets highlighted on a city map.

Usage:
    python -m python_pkg.warsaw_streets.warsaw_streets_anki

Output:
    Creates a self-contained .apkg file that can be directly imported into Anki.
"""

from __future__ import annotations

import argparse
import hashlib
from io import BytesIO
from pathlib import Path
import random
import sys
from typing import TYPE_CHECKING, Any

sys.path.insert(0, str(Path(__file__).parent.parent))
import genanki
from geo_data import get_warsaw_streets
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import MultiLineString

if TYPE_CHECKING:
    from collections.abc import Sequence

    from matplotlib.figure import Figure

# Minimum street length in meters to include
MIN_STREET_LENGTH = 500


def get_unique_streets(
    gdf: gpd.GeoDataFrame,
) -> list[tuple[str, gpd.GeoDataFrame, float]]:
    """Group street segments by name and merge geometries.

    Args:
        gdf: GeoDataFrame with street segments.

    Returns:
        List of (name, GeoDataFrame, length_m) tuples, sorted by length (longest first).
    """
    # Group by street name
    streets: dict[str, list[Any]] = {}
    for _, row in gdf.iterrows():
        name = row["name"]
        if name and name != "Unknown":
            if name not in streets:
                streets[name] = []
            streets[name].append(row.geometry)

    # Merge geometries and calculate length
    result = []
    for name, geometries in streets.items():
        merged = geometries[0] if len(geometries) == 1 else MultiLineString(geometries)

        # Create a GeoDataFrame for this street
        street_gdf = gpd.GeoDataFrame(
            [{"name": name, "geometry": merged}], crs="EPSG:4326"
        )

        # Calculate length in meters (approximate)
        street_gdf_proj = street_gdf.to_crs("EPSG:2180")  # Polish coordinate system
        length = street_gdf_proj.geometry.length.iloc[0]

        if length >= MIN_STREET_LENGTH:
            result.append((name, street_gdf, length))

    # Sort by length (longest first)
    result.sort(key=lambda x: x[2], reverse=True)
    return result


def load_street_data() -> (
    tuple[list[tuple[str, gpd.GeoDataFrame, float]], gpd.GeoDataFrame]
):
    """Load Warsaw streets and boundary.

    Returns:
        Tuple of (streets list sorted by length, warsaw boundary GeoDataFrame).
    """
    streets_gdf = get_warsaw_streets(min_length=MIN_STREET_LENGTH)
    streets = get_unique_streets(streets_gdf)

    # Load Warsaw districts for boundary (reuse from warsaw_districts)
    districts_path = (
        Path(__file__).parent.parent / "warsaw_districts" / "warszawa-dzielnice.geojson"
    )
    if districts_path.exists():
        warsaw_gdf = gpd.read_file(districts_path)
        # Get just Warsaw boundary
        warsaw_boundary = warsaw_gdf[warsaw_gdf["name"] == "Warszawa"]
        if len(warsaw_boundary) == 0:
            # Dissolve all districts
            warsaw_boundary = gpd.GeoDataFrame(
                geometry=[warsaw_gdf.union_all()], crs=warsaw_gdf.crs
            )
    else:
        msg = "Warsaw boundary data not found"
        raise FileNotFoundError(msg)

    return streets, warsaw_boundary


# Color for highlighted street
STREET_COLOR = "#E74C3C"  # Red


def create_street_map(
    street_gdf: gpd.GeoDataFrame,
    warsaw_boundary: gpd.GeoDataFrame,
) -> Figure:
    """Create a map showing Warsaw with one street highlighted.

    Args:
        street_name: Name of the street.
        street_gdf: GeoDataFrame with the street geometry.
        warsaw_boundary: GeoDataFrame with Warsaw boundary.

    Returns:
        A matplotlib Figure object.
    """
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_alpha(0)
    ax.patch.set_alpha(0)

    # Plot Warsaw as a plain gray shape
    warsaw_boundary.plot(ax=ax, color="#D5D8DC", alpha=0.6)
    warsaw_boundary.boundary.plot(ax=ax, color="#2C3E50", linewidth=2)

    # Plot the highlighted street
    street_gdf.plot(ax=ax, color=STREET_COLOR, linewidth=4, alpha=0.9)

    # Set bounds to Warsaw
    bounds = warsaw_boundary.total_bounds
    ax.set_xlim(bounds[0], bounds[2])
    ax.set_ylim(bounds[1], bounds[3])

    return fig


def generate_street_image_bytes(
    street_gdf: gpd.GeoDataFrame,
    warsaw_boundary: gpd.GeoDataFrame,
) -> bytes:
    """Generate a street map image as bytes.

    Args:
        street_gdf: GeoDataFrame with the street geometry.
        warsaw_boundary: GeoDataFrame with Warsaw boundary.

    Returns:
        PNG image data as bytes.
    """
    fig = create_street_map(street_gdf, warsaw_boundary)

    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=150)
    plt.close(fig)
    buf.seek(0)

    return buf.read()


def generate_anki_package(
    streets: list[tuple[str, gpd.GeoDataFrame, float]],
    warsaw_boundary: gpd.GeoDataFrame,
    deck_name: str = "Warsaw Streets",
) -> genanki.Package:
    """Generate Anki package for Warsaw streets.

    Args:
        streets: List of (name, GeoDataFrame, length) tuples, sorted by length.
        warsaw_boundary: GeoDataFrame with Warsaw boundary.
        deck_name: Name for the Anki deck.

    Returns:
        genanki.Package object.
    """
    model_id_hash = hashlib.md5(f"warsaw_streets_{deck_name}".encode())  # noqa: S324
    model_id = int(model_id_hash.hexdigest()[:8], 16)

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
        "Warsaw Street Model",
        fields=[
            {"name": "StreetMap"},
            {"name": "StreetName"},
        ],
        templates=[
            {
                "name": "Card 1",
                "qfmt": '<div class="map-container">{{StreetMap}}</div>',
                "afmt": '<div class="map-container">{{StreetMap}}</div>'
                '<hr id="answer">'
                '<div class="answer-text">{{StreetName}}</div>',
            },
        ],
        css=card_css,
    )

    deck_id = random.randrange(1 << 30, 1 << 31)  # noqa: S311
    my_deck = genanki.Deck(deck_id, deck_name)
    media_files = []

    # Streets are already sorted by length (longest first)
    for street_name, street_gdf, _length in streets:
        image_data = generate_street_image_bytes(street_gdf, warsaw_boundary)
        filename = f"street_{street_name.replace(' ', '_').replace('/', '_')}.png"

        note = genanki.Note(
            model=my_model,
            fields=[f'<img src="{filename}">', street_name],
            tags=["geography", "warsaw", "streets"],
        )
        my_deck.add_note(note)

        temp_path = Path(f"/tmp/{filename}")  # noqa: S108
        temp_path.write_bytes(image_data)
        media_files.append(str(temp_path))

    package = genanki.Package(my_deck)
    package.media_files = media_files
    return package


def main(argv: Sequence[str] | None = None) -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate Anki flashcards for Warsaw streets.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Output file path (default: warsaw_streets.apkg)",
    )
    parser.add_argument(
        "--deck-name",
        "-d",
        type=str,
        default="Warsaw Streets",
        help="Name for the Anki deck",
    )
    parser.add_argument(
        "--min-length",
        "-m",
        type=int,
        default=MIN_STREET_LENGTH,
        help=f"Minimum street length in meters (default: {MIN_STREET_LENGTH})",
    )
    parser.add_argument(
        "--preview",
        "-p",
        type=str,
        default=None,
        help="Export preview images to specified directory",
    )
    parser.add_argument(
        "--preview-count",
        type=int,
        default=5,
        help="Number of preview images to export (default: 5)",
    )

    args = parser.parse_args(argv)
    output_path = Path(args.output) if args.output else Path("warsaw_streets.apkg")

    try:
        sys.stdout.write("Loading street data...\n")
        streets, warsaw_boundary = load_street_data()
        num_streets = len(streets)

        sys.stdout.write(f"Generating flashcards for {num_streets} Warsaw streets...\n")

        package = generate_anki_package(streets, warsaw_boundary, args.deck_name)
        package.write_to_file(str(output_path))

        # Export preview images if requested (top N longest streets)
        if args.preview:
            preview_dir = Path(args.preview)
            preview_dir.mkdir(parents=True, exist_ok=True)
            preview_streets = streets[: args.preview_count]
            sys.stdout.write(
                f"Exporting {len(preview_streets)} preview images "
                f"(longest streets) to {preview_dir}...\n"
            )
            for street_name, street_gdf, length_m in preview_streets:
                image_data = generate_street_image_bytes(street_gdf, warsaw_boundary)
                safe_name = street_name.replace(" ", "_").replace("/", "_")
                preview_path = preview_dir / f"{safe_name}.png"
                preview_path.write_bytes(image_data)
                sys.stdout.write(f"  Saved: {preview_path.name} ({length_m:.0f}m)\n")

        sys.stdout.write("\n")
        sys.stdout.write("=" * 60 + "\n")
        sys.stdout.write("FLASHCARD GENERATION COMPLETE\n")
        sys.stdout.write("=" * 60 + "\n")
        sys.stdout.write(f"Streets: {num_streets}\n")
        sys.stdout.write(f"Output file: {output_path.absolute()}\n")
        if args.preview:
            sys.stdout.write(f"Preview images: {args.preview}\n")
    except (OSError, ValueError, RuntimeError) as e:
        sys.stderr.write(f"Error: {e}\n")
        return 1
    else:
        return 0


if __name__ == "__main__":
    sys.exit(main())
