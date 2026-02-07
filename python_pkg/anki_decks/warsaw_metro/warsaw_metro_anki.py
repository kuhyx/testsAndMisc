#!/usr/bin/env python3
"""Anki flashcard generator for Warsaw metro stations.

Generates Anki-compatible flashcard decks with maps showing individual
Warsaw metro stations highlighted on a city map.
"""

from __future__ import annotations

import argparse
import hashlib
from io import BytesIO
from pathlib import Path
import random
import sys
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).parent.parent))
import genanki
from geo_data import get_warsaw_metro_stations
import geopandas as gpd
import matplotlib.pyplot as plt

if TYPE_CHECKING:
    from collections.abc import Sequence

    from matplotlib.figure import Figure

# Station marker color
STATION_COLOR = "#E74C3C"


def load_warsaw_boundary() -> gpd.GeoDataFrame:
    """Load Warsaw boundary from districts GeoJSON.

    Returns:
        GeoDataFrame with Warsaw boundary.
    """
    districts_path = (
        Path(__file__).parent.parent / "warsaw_districts" / "warszawa-dzielnice.geojson"
    )
    if districts_path.exists():
        warsaw_gdf = gpd.read_file(districts_path)
        warsaw_boundary = warsaw_gdf[warsaw_gdf["name"] == "Warszawa"]
        if len(warsaw_boundary) == 0:
            warsaw_boundary = gpd.GeoDataFrame(
                geometry=[warsaw_gdf.union_all()], crs=warsaw_gdf.crs
            )
        return warsaw_boundary

    msg = "Warsaw boundary data not found"
    raise FileNotFoundError(msg)


def create_station_map(
    station_gdf: gpd.GeoDataFrame,
    warsaw_boundary: gpd.GeoDataFrame,
) -> Figure:
    """Create a map showing Warsaw with one metro station highlighted.

    Args:
        station_gdf: GeoDataFrame with the station point.
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

    # Plot the station as a large dot
    station_gdf.plot(
        ax=ax,
        color=STATION_COLOR,
        markersize=300,
        marker="o",
        alpha=0.9,
        edgecolor="#1A1A1A",
        linewidth=2,
    )

    # Set bounds to Warsaw
    bounds = warsaw_boundary.total_bounds
    ax.set_xlim(bounds[0], bounds[2])
    ax.set_ylim(bounds[1], bounds[3])

    return fig


def generate_station_image_bytes(
    station_gdf: gpd.GeoDataFrame,
    warsaw_boundary: gpd.GeoDataFrame,
) -> bytes:
    """Generate a station map image as bytes."""
    fig = create_station_map(station_gdf, warsaw_boundary)

    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=150)
    plt.close(fig)
    buf.seek(0)

    return buf.read()


def generate_anki_package(
    stations: gpd.GeoDataFrame,
    warsaw_boundary: gpd.GeoDataFrame,
    deck_name: str = "Warsaw Metro Stations",
) -> genanki.Package:
    """Generate Anki package for Warsaw metro stations."""
    model_id_hash = hashlib.md5(f"warsaw_metro_{deck_name}".encode())  # noqa: S324
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
.line-info {
    font-size: 24px;
    margin-top: 10px;
    color: #666;
}
.card.night_mode .answer-text {
    color: #ECF0F1;
}
.card.night_mode .line-info {
    color: #AAA;
}
"""

    my_model = genanki.Model(
        model_id,
        "Warsaw Metro Model",
        fields=[
            {"name": "StationMap"},
            {"name": "StationName"},
            {"name": "Line"},
        ],
        templates=[
            {
                "name": "Card 1",
                "qfmt": '<div class="map-container">{{StationMap}}</div>',
                "afmt": '<div class="map-container">{{StationMap}}</div>'
                '<hr id="answer">'
                '<div class="answer-text">{{StationName}}</div>'
                '<div class="line-info">{{Line}}</div>',
            },
        ],
        css=card_css,
    )

    deck_id = random.randrange(1 << 30, 1 << 31)  # noqa: S311
    my_deck = genanki.Deck(deck_id, deck_name)
    media_files = []

    for _, row in stations.iterrows():
        station_name = row["name"]
        line = row.get("line", "")
        station_gdf = gpd.GeoDataFrame([row], crs=stations.crs)

        image_data = generate_station_image_bytes(station_gdf, warsaw_boundary)
        filename = f"metro_{station_name.replace(' ', '_').replace('/', '_')}.png"

        note = genanki.Note(
            model=my_model,
            fields=[f'<img src="{filename}">', station_name, line],
            tags=["geography", "warsaw", "metro"],
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
        description="Generate Anki flashcards for Warsaw metro stations.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Output file path (default: warsaw_metro.apkg)",
    )
    parser.add_argument(
        "--deck-name",
        "-d",
        type=str,
        default="Warsaw Metro Stations",
        help="Name for the Anki deck",
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
    output_path = Path(args.output) if args.output else Path("warsaw_metro.apkg")

    try:
        sys.stdout.write("Loading metro station data...\n")
        stations = get_warsaw_metro_stations()
        warsaw_boundary = load_warsaw_boundary()
        num_stations = len(stations)

        sys.stdout.write(
            f"Generating flashcards for {num_stations} metro stations...\n"
        )

        package = generate_anki_package(stations, warsaw_boundary, args.deck_name)
        package.write_to_file(str(output_path))

        # Export preview images if requested
        if args.preview:
            preview_dir = Path(args.preview)
            preview_dir.mkdir(parents=True, exist_ok=True)
            preview_stations = list(stations.iterrows())[: args.preview_count]
            sys.stdout.write(
                f"Exporting {len(preview_stations)} preview images "
                f"to {preview_dir}...\n"
            )
            for _, row in preview_stations:
                station_name = row["name"]
                station_gdf = gpd.GeoDataFrame([row], crs=stations.crs)
                image_data = generate_station_image_bytes(station_gdf, warsaw_boundary)
                safe_name = station_name.replace(" ", "_").replace("/", "_")
                preview_path = preview_dir / f"{safe_name}.png"
                preview_path.write_bytes(image_data)
                sys.stdout.write(f"  Saved: {preview_path.name}\n")

        sys.stdout.write("\n")
        sys.stdout.write("=" * 60 + "\n")
        sys.stdout.write("FLASHCARD GENERATION COMPLETE\n")
        sys.stdout.write("=" * 60 + "\n")
        sys.stdout.write(f"Stations: {num_stations}\n")
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
