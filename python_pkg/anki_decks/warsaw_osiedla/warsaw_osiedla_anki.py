#!/usr/bin/env python3
"""Anki flashcard generator for Warsaw osiedla (neighborhoods).

Generates Anki-compatible flashcard decks with maps showing individual
Warsaw neighborhoods highlighted on a city map.
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
from geo_data import get_warsaw_osiedla
import geopandas as gpd
import matplotlib.pyplot as plt

if TYPE_CHECKING:
    from collections.abc import Sequence

    from matplotlib.figure import Figure

# 50 unique colors for neighborhoods
OSIEDLE_COLORS = [
    "#E74C3C",
    "#3498DB",
    "#2ECC71",
    "#9B59B6",
    "#F39C12",
    "#1ABC9C",
    "#E91E63",
    "#00BCD4",
    "#8BC34A",
    "#FF5722",
    "#673AB7",
    "#FFEB3B",
    "#795548",
    "#607D8B",
    "#CDDC39",
    "#FF9800",
    "#4CAF50",
    "#03A9F4",
    "#F44336",
    "#009688",
    "#3F51B5",
    "#FFC107",
    "#9E9E9E",
    "#00E676",
    "#FF4081",
    "#448AFF",
    "#69F0AE",
    "#FFD740",
    "#40C4FF",
    "#B388FF",
    "#EA80FC",
    "#82B1FF",
    "#A7FFEB",
    "#FFFF8D",
    "#FF80AB",
    "#536DFE",
    "#64FFDA",
    "#FFE57F",
    "#80D8FF",
    "#B9F6CA",
    "#CF6679",
    "#BB86FC",
    "#03DAC6",
    "#018786",
    "#6200EE",
    "#3700B3",
    "#B00020",
    "#FF0266",
    "#C51162",
    "#AA00FF",
]


def load_warsaw_boundary() -> gpd.GeoDataFrame:
    """Load Warsaw boundary from districts GeoJSON."""
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


def create_osiedle_map(
    osiedle_name: str,
    osiedle_gdf: gpd.GeoDataFrame,
    warsaw_boundary: gpd.GeoDataFrame,
    all_osiedla: gpd.GeoDataFrame,
) -> Figure:
    """Create a map showing Warsaw with one osiedle highlighted."""
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_alpha(0)
    ax.patch.set_alpha(0)

    # Plot Warsaw as a plain gray shape
    warsaw_boundary.plot(ax=ax, color="#D5D8DC", alpha=0.6)
    warsaw_boundary.boundary.plot(ax=ax, color="#2C3E50", linewidth=2)

    # Assign color based on sorted names
    sorted_names = sorted(all_osiedla["name"].tolist())
    color_idx = sorted_names.index(osiedle_name) % len(OSIEDLE_COLORS)
    fill_color = OSIEDLE_COLORS[color_idx]

    # Plot the highlighted osiedle
    osiedle_gdf.plot(ax=ax, color=fill_color, alpha=0.9)
    osiedle_gdf.boundary.plot(ax=ax, color="#1A1A1A", linewidth=4)

    # Set bounds to Warsaw
    bounds = warsaw_boundary.total_bounds
    ax.set_xlim(bounds[0], bounds[2])
    ax.set_ylim(bounds[1], bounds[3])

    return fig


def generate_osiedle_image_bytes(
    osiedle_name: str,
    osiedle_gdf: gpd.GeoDataFrame,
    warsaw_boundary: gpd.GeoDataFrame,
    all_osiedla: gpd.GeoDataFrame,
) -> bytes:
    """Generate an osiedle map image as bytes."""
    fig = create_osiedle_map(osiedle_name, osiedle_gdf, warsaw_boundary, all_osiedla)

    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=150)
    plt.close(fig)
    buf.seek(0)

    return buf.read()


def generate_anki_package(
    osiedla: gpd.GeoDataFrame,
    warsaw_boundary: gpd.GeoDataFrame,
    deck_name: str = "Warsaw Osiedla",
) -> genanki.Package:
    """Generate Anki package for Warsaw osiedla."""
    model_id_hash = hashlib.md5(f"warsaw_osiedla_{deck_name}".encode())  # noqa: S324
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
        "Warsaw Osiedle Model",
        fields=[
            {"name": "OsiedleMap"},
            {"name": "OsiedleName"},
        ],
        templates=[
            {
                "name": "Card 1",
                "qfmt": '<div class="map-container">{{OsiedleMap}}</div>',
                "afmt": '<div class="map-container">{{OsiedleMap}}</div>'
                '<hr id="answer">'
                '<div class="answer-text">{{OsiedleName}}</div>',
            },
        ],
        css=card_css,
    )

    deck_id = random.randrange(1 << 30, 1 << 31)  # noqa: S311
    my_deck = genanki.Deck(deck_id, deck_name)
    media_files = []

    for _, row in osiedla.iterrows():
        osiedle_name = row["name"]
        osiedle_gdf = gpd.GeoDataFrame([row], crs=osiedla.crs)

        image_data = generate_osiedle_image_bytes(
            osiedle_name, osiedle_gdf, warsaw_boundary, osiedla
        )
        filename = f"osiedle_{osiedle_name.replace(' ', '_').replace('/', '_')}.png"

        note = genanki.Note(
            model=my_model,
            fields=[f'<img src="{filename}">', osiedle_name],
            tags=["geography", "warsaw", "osiedla"],
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
        description="Generate Anki flashcards for Warsaw osiedla.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Output file path (default: warsaw_osiedla.apkg)",
    )
    parser.add_argument(
        "--deck-name",
        "-d",
        type=str,
        default="Warsaw Osiedla",
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
    output_path = Path(args.output) if args.output else Path("warsaw_osiedla.apkg")

    try:
        sys.stdout.write("Loading osiedla data...\n")
        osiedla = get_warsaw_osiedla()
        warsaw_boundary = load_warsaw_boundary()
        num_osiedla = len(osiedla)

        sys.stdout.write(f"Generating flashcards for {num_osiedla} osiedla...\n")

        package = generate_anki_package(osiedla, warsaw_boundary, args.deck_name)
        package.write_to_file(str(output_path))

        # Export preview images if requested
        if args.preview:
            preview_dir = Path(args.preview)
            preview_dir.mkdir(parents=True, exist_ok=True)
            preview_osiedla = list(osiedla.iterrows())[: args.preview_count]
            sys.stdout.write(
                f"Exporting {len(preview_osiedla)} preview images "
                f"to {preview_dir}...\n"
            )
            for _, row in preview_osiedla:
                osiedle_name = row["name"]
                osiedle_gdf = gpd.GeoDataFrame([row], crs=osiedla.crs)
                image_data = generate_osiedle_image_bytes(
                    osiedle_name, osiedle_gdf, warsaw_boundary, osiedla
                )
                safe_name = osiedle_name.replace(" ", "_").replace("/", "_")
                preview_path = preview_dir / f"{safe_name}.png"
                preview_path.write_bytes(image_data)
                sys.stdout.write(f"  Saved: {preview_path.name}\n")

        sys.stdout.write("\n")
        sys.stdout.write("=" * 60 + "\n")
        sys.stdout.write("FLASHCARD GENERATION COMPLETE\n")
        sys.stdout.write("=" * 60 + "\n")
        sys.stdout.write(f"Osiedla: {num_osiedla}\n")
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
