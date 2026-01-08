#!/usr/bin/env python3
"""Anki flashcard generator for Polish gminy (municipalities).

Generates Anki-compatible flashcard decks with maps showing individual
Polish municipalities highlighted on a country map.

Uses multiprocessing to parallelize image generation for ~4x speedup.
"""

from __future__ import annotations

import argparse
import hashlib
from io import BytesIO
import multiprocessing as mp
from pathlib import Path
import random
import sys
import tempfile
from typing import TYPE_CHECKING

import genanki
import geopandas as gpd
import matplotlib as mpl

mpl.use("Agg")  # Non-interactive backend for multiprocessing
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).parent.parent))
from geo_data import get_poland_boundary, get_polish_gminy

if TYPE_CHECKING:
    from collections.abc import Sequence

    from matplotlib.figure import Figure

# 2500 colors for gminy (cycling through)
GMINA_COLORS = [
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


def create_gmina_map(
    gmina_name: str,
    gmina_gdf: gpd.GeoDataFrame,
    poland_boundary: gpd.GeoDataFrame,
    color_map: dict[str, str],
) -> Figure:
    """Create a map showing Poland with one gmina highlighted."""
    fig, ax = plt.subplots(figsize=(10, 12))
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_alpha(0)
    ax.patch.set_alpha(0)

    # Plot Poland as a plain gray shape
    poland_boundary.plot(ax=ax, color="#D5D8DC", alpha=0.6)
    poland_boundary.boundary.plot(ax=ax, color="#2C3E50", linewidth=1)

    # Get pre-computed color
    fill_color = color_map.get(gmina_name, GMINA_COLORS[0])

    # Plot the highlighted gmina
    gmina_gdf.plot(ax=ax, color=fill_color, alpha=0.9)
    gmina_gdf.boundary.plot(ax=ax, color="#1A1A1A", linewidth=3)

    # Set bounds to Poland
    bounds = poland_boundary.total_bounds
    ax.set_xlim(bounds[0], bounds[2])
    ax.set_ylim(bounds[1], bounds[3])

    return fig


def generate_gmina_image_bytes(
    gmina_name: str,
    gmina_gdf: gpd.GeoDataFrame,
    poland_boundary: gpd.GeoDataFrame,
    color_map: dict[str, str],
) -> bytes:
    """Generate a gmina map image as bytes."""
    fig = create_gmina_map(gmina_name, gmina_gdf, poland_boundary, color_map)

    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=150)
    plt.close(fig)
    buf.seek(0)

    return buf.read()


def _build_color_map(names: list[str]) -> dict[str, str]:
    """Pre-compute color mapping for all names.

    Args:
        names: List of all gmina names.

    Returns:
        Dictionary mapping name to color.
    """
    sorted_names = sorted(names)
    return {
        name: GMINA_COLORS[i % len(GMINA_COLORS)] for i, name in enumerate(sorted_names)
    }


# Global variables for multiprocessing (set via initializer)
_mp_poland_boundary: gpd.GeoDataFrame | None = None
_mp_color_map: dict[str, str] | None = None


def _init_worker(
    poland_geojson: str,
    color_map: dict[str, str],
) -> None:
    """Initialize worker process with shared data."""
    global _mp_poland_boundary, _mp_color_map  # noqa: PLW0603
    _mp_poland_boundary = gpd.read_file(poland_geojson)
    _mp_color_map = color_map


def _render_single_gmina(args: tuple[str, str]) -> tuple[str, bytes]:
    """Render a single gmina image (worker function).

    Args:
        args: Tuple of (gmina_name, gmina_geojson_str).

    Returns:
        Tuple of (gmina_name, image_bytes).
    """
    gmina_name, gmina_geojson = args
    gmina_gdf = gpd.read_file(gmina_geojson)

    assert _mp_poland_boundary is not None  # noqa: S101
    assert _mp_color_map is not None  # noqa: S101

    image_data = generate_gmina_image_bytes(
        gmina_name, gmina_gdf, _mp_poland_boundary, _mp_color_map
    )
    return gmina_name, image_data


def generate_anki_package(
    gminy: gpd.GeoDataFrame,
    poland_boundary: gpd.GeoDataFrame,
    deck_name: str = "Polish Gminy",
) -> genanki.Package:
    """Generate Anki package for Polish gminy."""
    model_id_hash = hashlib.md5(f"polish_gminy_{deck_name}".encode())  # noqa: S324
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
        "Polish Gmina Model",
        fields=[
            {"name": "GminaMap"},
            {"name": "GminaName"},
        ],
        templates=[
            {
                "name": "Card 1",
                "qfmt": '<div class="map-container">{{GminaMap}}</div>',
                "afmt": '<div class="map-container">{{GminaMap}}</div>'
                '<hr id="answer">'
                '<div class="answer-text">{{GminaName}}</div>',
            },
        ],
        css=card_css,
    )

    deck_id = random.randrange(1 << 30, 1 << 31)  # noqa: S311
    my_deck = genanki.Deck(deck_id, deck_name)
    media_files = []

    # Pre-compute color mapping once (avoids O(n²) sorting)
    color_map = _build_color_map(gminy["name"].tolist())

    # Prepare data for parallel processing
    # Serialize GeoDataFrames to GeoJSON strings for pickling
    with tempfile.NamedTemporaryFile(suffix=".geojson", delete=False) as f:
        poland_boundary.to_file(f.name, driver="GeoJSON")
        poland_geojson_path = f.name

    # Prepare work items: (gmina_name, gmina_geojson_str)
    work_items: list[tuple[str, str]] = []
    for _, row in gminy.iterrows():
        gmina_gdf = gpd.GeoDataFrame([row], crs=gminy.crs)
        gmina_geojson = gmina_gdf.to_json()
        work_items.append((row["name"], gmina_geojson))

    # Use multiprocessing for parallel rendering
    num_workers = min(mp.cpu_count(), 8)
    sys.stdout.write(
        f"Rendering {len(work_items)} images using {num_workers} workers...\n"
    )

    results: dict[str, bytes] = {}
    with mp.Pool(
        num_workers,
        initializer=_init_worker,
        initargs=(poland_geojson_path, color_map),
    ) as pool:
        for i, (gmina_name, image_data) in enumerate(
            pool.imap_unordered(_render_single_gmina, work_items)
        ):
            results[gmina_name] = image_data
            if (i + 1) % 100 == 0:
                sys.stdout.write(f"  Rendered {i + 1}/{len(work_items)}...\n")

    # Clean up temp file
    Path(poland_geojson_path).unlink(missing_ok=True)

    # Create notes from results
    for _, row in gminy.iterrows():
        gmina_name = row["name"]
        image_data = results[gmina_name]
        filename = f"gmina_{gmina_name.replace(' ', '_').replace('/', '_')}.png"

        note = genanki.Note(
            model=my_model,
            fields=[f'<img src="{filename}">', gmina_name],
            tags=["geography", "poland", "gminy"],
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
        description="Generate Anki flashcards for Polish gminy.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Output file path (default: polish_gminy.apkg)",
    )
    parser.add_argument(
        "--deck-name",
        "-d",
        type=str,
        default="Polish Gminy",
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
    output_path = Path(args.output) if args.output else Path("polish_gminy.apkg")

    try:
        sys.stdout.write("Loading gminy data...\n")
        gminy = get_polish_gminy()
        poland_boundary = get_poland_boundary()
        num_gminy = len(gminy)

        sys.stdout.write(f"Generating flashcards for {num_gminy} gminy...\n")
        sys.stdout.write("This will take a while for ~2500 gminy...\n")

        package = generate_anki_package(gminy, poland_boundary, args.deck_name)
        package.write_to_file(str(output_path))

        # Export preview images if requested
        if args.preview:
            preview_dir = Path(args.preview)
            preview_dir.mkdir(parents=True, exist_ok=True)
            preview_gminy = list(gminy.iterrows())[: args.preview_count]
            # Pre-compute color mapping for previews
            color_map = _build_color_map(gminy["name"].tolist())
            sys.stdout.write(
                f"Exporting {len(preview_gminy)} preview images "
                f"to {preview_dir}...\n"
            )
            for _, row in preview_gminy:
                gmina_name = row["name"]
                gmina_gdf = gpd.GeoDataFrame([row], crs=gminy.crs)
                image_data = generate_gmina_image_bytes(
                    gmina_name, gmina_gdf, poland_boundary, color_map
                )
                safe_name = gmina_name.replace(" ", "_").replace("/", "_")
                preview_path = preview_dir / f"{safe_name}.png"
                preview_path.write_bytes(image_data)
                sys.stdout.write(f"  Saved: {preview_path.name}\n")

        sys.stdout.write("\n")
        sys.stdout.write("=" * 60 + "\n")
        sys.stdout.write("FLASHCARD GENERATION COMPLETE\n")
        sys.stdout.write("=" * 60 + "\n")
        sys.stdout.write(f"Gminy: {num_gminy}\n")
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
