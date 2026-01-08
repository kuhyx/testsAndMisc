#!/usr/bin/env python3
"""Anki flashcard generator for Warsaw landmarks.

Generates Anki-compatible flashcard decks with maps showing individual
Warsaw landmarks (monuments, museums, parks, historic sites).
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
from geo_data import get_warsaw_landmarks
import geopandas as gpd
import matplotlib.pyplot as plt

if TYPE_CHECKING:
    from collections.abc import Sequence

    from matplotlib.figure import Figure

# Landmark marker color
LANDMARK_COLOR = "#9B59B6"  # Purple


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


def create_landmark_map(
    landmark_gdf: gpd.GeoDataFrame,
    warsaw_boundary: gpd.GeoDataFrame,
) -> Figure:
    """Create a map showing Warsaw with one landmark highlighted."""
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_alpha(0)
    ax.patch.set_alpha(0)

    # Plot Warsaw as a plain gray shape
    warsaw_boundary.plot(ax=ax, color="#D5D8DC", alpha=0.6)
    warsaw_boundary.boundary.plot(ax=ax, color="#2C3E50", linewidth=2)

    # Plot the landmark as a star marker
    landmark_gdf.plot(
        ax=ax,
        color=LANDMARK_COLOR,
        markersize=400,
        marker="*",
        alpha=0.9,
        edgecolor="#1A1A1A",
        linewidth=1.5,
    )

    # Set bounds to Warsaw
    bounds = warsaw_boundary.total_bounds
    ax.set_xlim(bounds[0], bounds[2])
    ax.set_ylim(bounds[1], bounds[3])

    return fig


def generate_landmark_image_bytes(
    landmark_gdf: gpd.GeoDataFrame,
    warsaw_boundary: gpd.GeoDataFrame,
) -> bytes:
    """Generate a landmark map image as bytes."""
    fig = create_landmark_map(landmark_gdf, warsaw_boundary)

    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=150)
    plt.close(fig)
    buf.seek(0)

    return buf.read()


def generate_anki_package(
    landmarks: gpd.GeoDataFrame,
    warsaw_boundary: gpd.GeoDataFrame,
    deck_name: str = "Warsaw Landmarks",
) -> genanki.Package:
    """Generate Anki package for Warsaw landmarks."""
    model_id_hash = hashlib.md5(f"warsaw_landmarks_{deck_name}".encode())  # noqa: S324
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
        "Warsaw Landmark Model",
        fields=[
            {"name": "LandmarkMap"},
            {"name": "LandmarkName"},
        ],
        templates=[
            {
                "name": "Card 1",
                "qfmt": '<div class="map-container">{{LandmarkMap}}</div>',
                "afmt": '<div class="map-container">{{LandmarkMap}}</div>'
                '<hr id="answer">'
                '<div class="answer-text">{{LandmarkName}}</div>',
            },
        ],
        css=card_css,
    )

    deck_id = random.randrange(1 << 30, 1 << 31)  # noqa: S311
    my_deck = genanki.Deck(deck_id, deck_name)
    media_files = []

    for _, row in landmarks.iterrows():
        landmark_name = row["name"]
        landmark_gdf = gpd.GeoDataFrame([row], crs=landmarks.crs)

        image_data = generate_landmark_image_bytes(landmark_gdf, warsaw_boundary)
        filename = f"landmark_{landmark_name.replace(' ', '_').replace('/', '_')}.png"

        note = genanki.Note(
            model=my_model,
            fields=[f'<img src="{filename}">', landmark_name],
            tags=["geography", "warsaw", "landmarks"],
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
        description="Generate Anki flashcards for Warsaw landmarks.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Output file path (default: warsaw_landmarks.apkg)",
    )
    parser.add_argument(
        "--deck-name",
        "-d",
        type=str,
        default="Warsaw Landmarks",
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
    output_path = Path(args.output) if args.output else Path("warsaw_landmarks.apkg")

    try:
        sys.stdout.write("Loading landmark data...\n")
        landmarks = get_warsaw_landmarks()
        warsaw_boundary = load_warsaw_boundary()
        num_landmarks = len(landmarks)

        sys.stdout.write(f"Generating flashcards for {num_landmarks} landmarks...\n")

        package = generate_anki_package(landmarks, warsaw_boundary, args.deck_name)
        package.write_to_file(str(output_path))

        # Export preview images if requested
        if args.preview:
            preview_dir = Path(args.preview)
            preview_dir.mkdir(parents=True, exist_ok=True)
            preview_landmarks = list(landmarks.iterrows())[: args.preview_count]
            sys.stdout.write(
                f"Exporting {len(preview_landmarks)} preview images "
                f"to {preview_dir}...\n"
            )
            for _, row in preview_landmarks:
                landmark_name = row["name"]
                landmark_gdf = gpd.GeoDataFrame([row], crs=landmarks.crs)
                image_data = generate_landmark_image_bytes(
                    landmark_gdf, warsaw_boundary
                )
                safe_name = landmark_name.replace(" ", "_").replace("/", "_")
                preview_path = preview_dir / f"{safe_name}.png"
                preview_path.write_bytes(image_data)
                sys.stdout.write(f"  Saved: {preview_path.name}\n")

        sys.stdout.write("\n")
        sys.stdout.write("=" * 60 + "\n")
        sys.stdout.write("FLASHCARD GENERATION COMPLETE\n")
        sys.stdout.write("=" * 60 + "\n")
        sys.stdout.write(f"Landmarks: {num_landmarks}\n")
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
