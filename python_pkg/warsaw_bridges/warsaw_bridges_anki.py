#!/usr/bin/env python3
"""Anki flashcard generator for Warsaw bridges over the Vistula.

Generates Anki-compatible flashcard decks with maps showing individual
Warsaw bridges highlighted on a city map.
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

# Import shared data module
sys.path.insert(0, str(Path(__file__).parent.parent))
from geo_data import get_vistula_river, get_warsaw_bridges

if TYPE_CHECKING:
    from collections.abc import Sequence

    from matplotlib.figure import Figure

# Bridge color
BRIDGE_COLOR = "#E74C3C"  # Red
RIVER_COLOR = "#3498DB"  # Blue


def load_warsaw_boundary() -> gpd.GeoDataFrame:
    """Load Warsaw boundary from districts GeoJSON.

    Returns:
        GeoDataFrame with Warsaw boundary.

    Raises:
        FileNotFoundError: If boundary data file not found.
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


def create_bridge_map(
    bridge_gdf: gpd.GeoDataFrame,
    warsaw_boundary: gpd.GeoDataFrame,
    vistula: gpd.GeoDataFrame,
) -> Figure:
    """Create a map showing Warsaw with one bridge highlighted.

    Args:
        bridge_gdf: GeoDataFrame with the bridge to highlight.
        warsaw_boundary: GeoDataFrame with Warsaw boundary.
        vistula: GeoDataFrame with Vistula river geometry.

    Returns:
        Matplotlib figure with the map.
    """
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_alpha(0)
    ax.patch.set_alpha(0)

    # Plot Warsaw as a plain gray shape
    warsaw_boundary.plot(ax=ax, color="#D5D8DC", alpha=0.6)
    warsaw_boundary.boundary.plot(ax=ax, color="#2C3E50", linewidth=2)

    # Plot Vistula river
    vistula.plot(ax=ax, color=RIVER_COLOR, linewidth=3, alpha=0.7)

    # Plot the bridge
    bridge_gdf.plot(ax=ax, color=BRIDGE_COLOR, linewidth=6, alpha=0.9)

    # Set bounds to Warsaw
    bounds = warsaw_boundary.total_bounds
    ax.set_xlim(bounds[0], bounds[2])
    ax.set_ylim(bounds[1], bounds[3])

    return fig


def generate_bridge_image_bytes(
    bridge_gdf: gpd.GeoDataFrame,
    warsaw_boundary: gpd.GeoDataFrame,
    vistula: gpd.GeoDataFrame,
) -> bytes:
    """Generate a bridge map image as bytes.

    Args:
        bridge_gdf: GeoDataFrame with the bridge.
        warsaw_boundary: GeoDataFrame with Warsaw boundary.
        vistula: GeoDataFrame with Vistula river.

    Returns:
        PNG image bytes.
    """
    fig = create_bridge_map(bridge_gdf, warsaw_boundary, vistula)

    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=150)
    plt.close(fig)
    buf.seek(0)

    return buf.read()


def generate_anki_package(
    bridges: gpd.GeoDataFrame,
    warsaw_boundary: gpd.GeoDataFrame,
    vistula: gpd.GeoDataFrame,
    deck_name: str = "Warsaw Bridges",
) -> genanki.Package:
    """Generate Anki package for Warsaw bridges.

    Args:
        bridges: GeoDataFrame with all bridges.
        warsaw_boundary: GeoDataFrame with Warsaw boundary.
        vistula: GeoDataFrame with Vistula river.
        deck_name: Name for the Anki deck.

    Returns:
        Generated Anki package.
    """
    model_id_hash = hashlib.md5(f"warsaw_bridges_{deck_name}".encode())  # noqa: S324
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
        "Warsaw Bridge Model",
        fields=[
            {"name": "BridgeMap"},
            {"name": "BridgeName"},
        ],
        templates=[
            {
                "name": "Card 1",
                "qfmt": '<div class="map-container">{{BridgeMap}}</div>',
                "afmt": '<div class="map-container">{{BridgeMap}}</div>'
                '<hr id="answer">'
                '<div class="answer-text">{{BridgeName}}</div>',
            },
        ],
        css=card_css,
    )

    deck_id = random.randrange(1 << 30, 1 << 31)  # noqa: S311
    my_deck = genanki.Deck(deck_id, deck_name)
    media_files = []

    for _, row in bridges.iterrows():
        bridge_name = row["name"]
        bridge_gdf = gpd.GeoDataFrame([row], crs=bridges.crs)

        image_data = generate_bridge_image_bytes(bridge_gdf, warsaw_boundary, vistula)
        filename = f"bridge_{bridge_name.replace(' ', '_').replace('/', '_')}.png"

        note = genanki.Note(
            model=my_model,
            fields=[f'<img src="{filename}">', bridge_name],
            tags=["geography", "warsaw", "bridges"],
        )
        my_deck.add_note(note)

        temp_path = Path(f"/tmp/{filename}")  # noqa: S108
        temp_path.write_bytes(image_data)
        media_files.append(str(temp_path))

    package = genanki.Package(my_deck)
    package.media_files = media_files
    return package


def main(argv: Sequence[str] | None = None) -> int:
    """Main entry point.

    Args:
        argv: Command-line arguments.

    Returns:
        Exit code.
    """
    parser = argparse.ArgumentParser(
        description="Generate Anki flashcards for Warsaw bridges.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Output file path (default: warsaw_bridges.apkg)",
    )
    parser.add_argument(
        "--deck-name",
        "-d",
        type=str,
        default="Warsaw Bridges",
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
    output_path = Path(args.output) if args.output else Path("warsaw_bridges.apkg")

    try:
        sys.stdout.write("Loading bridge data...\n")
        bridges = get_warsaw_bridges()
        vistula = get_vistula_river()
        warsaw_boundary = load_warsaw_boundary()
        num_bridges = len(bridges)

        sys.stdout.write(f"Generating flashcards for {num_bridges} bridges...\n")

        package = generate_anki_package(
            bridges, warsaw_boundary, vistula, args.deck_name
        )
        package.write_to_file(str(output_path))

        # Export preview images if requested
        if args.preview:
            preview_dir = Path(args.preview)
            preview_dir.mkdir(parents=True, exist_ok=True)
            preview_bridges = list(bridges.iterrows())[: args.preview_count]
            sys.stdout.write(
                f"Exporting {len(preview_bridges)} preview images "
                f"to {preview_dir}...\n"
            )
            for _, row in preview_bridges:
                bridge_name = row["name"]
                bridge_gdf = gpd.GeoDataFrame([row], crs=bridges.crs)
                image_data = generate_bridge_image_bytes(
                    bridge_gdf, warsaw_boundary, vistula
                )
                safe_name = bridge_name.replace(" ", "_").replace("/", "_")
                preview_path = preview_dir / f"{safe_name}.png"
                preview_path.write_bytes(image_data)
                sys.stdout.write(f"  Saved: {preview_path.name}\n")

        sys.stdout.write("\n")
        sys.stdout.write("=" * 60 + "\n")
        sys.stdout.write("FLASHCARD GENERATION COMPLETE\n")
        sys.stdout.write("=" * 60 + "\n")
        sys.stdout.write(f"Bridges: {num_bridges}\n")
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
