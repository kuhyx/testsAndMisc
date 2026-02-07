#!/usr/bin/env python3
"""Anki flashcard generator for Polish powiaty (counties).

Generates Anki-compatible flashcard decks with maps showing individual
Polish counties highlighted on a country map.
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

sys.path.insert(0, str(Path(__file__).parent.parent))
from geo_data import get_poland_boundary, get_polish_powiaty

if TYPE_CHECKING:
    from collections.abc import Sequence

    from matplotlib.figure import Figure

# 400 distinct colors for powiaty (cycling through)
POWIAT_COLORS = [
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


def create_powiat_map(
    powiat_name: str,
    powiat_gdf: gpd.GeoDataFrame,
    poland_boundary: gpd.GeoDataFrame,
    all_powiaty: gpd.GeoDataFrame,
) -> Figure:
    """Create a map showing Poland with one powiat highlighted."""
    fig, ax = plt.subplots(figsize=(10, 12))
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_alpha(0)
    ax.patch.set_alpha(0)

    # Plot Poland as a plain gray shape
    poland_boundary.plot(ax=ax, color="#D5D8DC", alpha=0.6)
    poland_boundary.boundary.plot(ax=ax, color="#2C3E50", linewidth=1)

    # Assign color based on sorted names
    sorted_names = sorted(all_powiaty["nazwa"].tolist())
    color_idx = sorted_names.index(powiat_name) % len(POWIAT_COLORS)
    fill_color = POWIAT_COLORS[color_idx]

    # Plot the highlighted powiat
    powiat_gdf.plot(ax=ax, color=fill_color, alpha=0.9)
    powiat_gdf.boundary.plot(ax=ax, color="#1A1A1A", linewidth=3)

    # Set bounds to Poland
    bounds = poland_boundary.total_bounds
    ax.set_xlim(bounds[0], bounds[2])
    ax.set_ylim(bounds[1], bounds[3])

    return fig


def generate_powiat_image_bytes(
    powiat_name: str,
    powiat_gdf: gpd.GeoDataFrame,
    poland_boundary: gpd.GeoDataFrame,
    all_powiaty: gpd.GeoDataFrame,
) -> bytes:
    """Generate a powiat map image as bytes."""
    fig = create_powiat_map(powiat_name, powiat_gdf, poland_boundary, all_powiaty)

    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=150)
    plt.close(fig)
    buf.seek(0)

    return buf.read()


def generate_anki_package(
    powiaty: gpd.GeoDataFrame,
    poland_boundary: gpd.GeoDataFrame,
    deck_name: str = "Polish Powiaty",
) -> genanki.Package:
    """Generate Anki package for Polish powiaty."""
    model_id_hash = hashlib.md5(f"polish_powiaty_{deck_name}".encode())  # noqa: S324
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
        "Polish Powiat Model",
        fields=[
            {"name": "PowiatMap"},
            {"name": "PowiatName"},
        ],
        templates=[
            {
                "name": "Card 1",
                "qfmt": '<div class="map-container">{{PowiatMap}}</div>',
                "afmt": '<div class="map-container">{{PowiatMap}}</div>'
                '<hr id="answer">'
                '<div class="answer-text">{{PowiatName}}</div>',
            },
        ],
        css=card_css,
    )

    deck_id = random.randrange(1 << 30, 1 << 31)  # noqa: S311
    my_deck = genanki.Deck(deck_id, deck_name)
    media_files = []

    for _, row in powiaty.iterrows():
        powiat_name = row["nazwa"]
        powiat_gdf = gpd.GeoDataFrame([row], crs=powiaty.crs)

        image_data = generate_powiat_image_bytes(
            powiat_name, powiat_gdf, poland_boundary, powiaty
        )
        filename = f"powiat_{powiat_name.replace(' ', '_').replace('/', '_')}.png"

        note = genanki.Note(
            model=my_model,
            fields=[f'<img src="{filename}">', powiat_name],
            tags=["geography", "poland", "powiaty"],
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
        description="Generate Anki flashcards for Polish powiaty.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Output file path (default: polish_powiaty.apkg)",
    )
    parser.add_argument(
        "--deck-name",
        "-d",
        type=str,
        default="Polish Powiaty",
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
    output_path = Path(args.output) if args.output else Path("polish_powiaty.apkg")

    try:
        sys.stdout.write("Loading powiaty data...\n")
        powiaty = get_polish_powiaty()
        poland_boundary = get_poland_boundary()
        num_powiaty = len(powiaty)

        sys.stdout.write(f"Generating flashcards for {num_powiaty} powiaty...\n")

        package = generate_anki_package(powiaty, poland_boundary, args.deck_name)
        package.write_to_file(str(output_path))

        # Export preview images if requested
        if args.preview:
            preview_dir = Path(args.preview)
            preview_dir.mkdir(parents=True, exist_ok=True)
            preview_powiaty = list(powiaty.iterrows())[: args.preview_count]
            sys.stdout.write(
                f"Exporting {len(preview_powiaty)} preview images "
                f"to {preview_dir}...\n"
            )
            for _, row in preview_powiaty:
                powiat_name = row["nazwa"]
                powiat_gdf = gpd.GeoDataFrame([row], crs=powiaty.crs)
                image_data = generate_powiat_image_bytes(
                    powiat_name, powiat_gdf, poland_boundary, powiaty
                )
                safe_name = powiat_name.replace(" ", "_").replace("/", "_")
                preview_path = preview_dir / f"{safe_name}.png"
                preview_path.write_bytes(image_data)
                sys.stdout.write(f"  Saved: {preview_path.name}\n")

        sys.stdout.write("\n")
        sys.stdout.write("=" * 60 + "\n")
        sys.stdout.write("FLASHCARD GENERATION COMPLETE\n")
        sys.stdout.write("=" * 60 + "\n")
        sys.stdout.write(f"Powiaty: {num_powiaty}\n")
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
