"""Anki flashcard generator for Polish islands.

Generates Anki-compatible flashcard decks with maps showing islands
highlighted on a Poland map.
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
from geo_data import get_poland_boundary, get_polish_islands

if TYPE_CHECKING:
    from collections.abc import Sequence

    from matplotlib.figure import Figure

ISLAND_COLOR = "#E67E22"  # Orange for islands
NEIGHBOR_COLOR = "#EAECEE"  # Lighter gray for extended view

# Padding for zoom (in degrees)
ZOOM_PADDING_DEG = 0.2


def _island_extends_beyond(
    island_gdf: gpd.GeoDataFrame,
    poland_boundary: gpd.GeoDataFrame,
) -> bool:
    """Check if island extends beyond Poland's boundaries."""
    poland_bounds = poland_boundary.total_bounds  # [minx, miny, maxx, maxy]
    island_bounds = island_gdf.total_bounds

    # Check if any part of island is outside Poland
    extends_west = island_bounds[0] < poland_bounds[0]
    extends_south = island_bounds[1] < poland_bounds[1]
    extends_east = island_bounds[2] > poland_bounds[2]
    extends_north = island_bounds[3] > poland_bounds[3]

    return extends_west or extends_south or extends_east or extends_north


def create_island_map(
    island_gdf: gpd.GeoDataFrame,
    poland_boundary: gpd.GeoDataFrame,
    *,
    zoom: bool,
) -> Figure:
    """Create a map showing Poland with one island highlighted.

    Args:
        island_gdf: GeoDataFrame with the island to highlight.
        poland_boundary: GeoDataFrame with Poland's boundary.
        zoom: If True, zoom to island area for better visibility.
    """
    fig, ax = plt.subplots(figsize=(10, 12))
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_alpha(0)
    ax.patch.set_alpha(0)

    extends_beyond = _island_extends_beyond(island_gdf, poland_boundary)

    if extends_beyond:
        # Draw extended background if island goes beyond Poland
        island_bounds = island_gdf.total_bounds
        padding = 0.5
        ax.fill(
            [
                island_bounds[0] - padding,
                island_bounds[2] + padding,
                island_bounds[2] + padding,
                island_bounds[0] - padding,
            ],
            [
                island_bounds[1] - padding,
                island_bounds[1] - padding,
                island_bounds[3] + padding,
                island_bounds[3] + padding,
            ],
            color=NEIGHBOR_COLOR,
            zorder=0,
        )

    # Plot Poland as a plain gray shape
    poland_boundary.plot(ax=ax, color="#D5D8DC", alpha=0.6)
    poland_boundary.boundary.plot(ax=ax, color="#2C3E50", linewidth=1)

    # Plot the island with thinner lines
    island_gdf.plot(ax=ax, color=ISLAND_COLOR, alpha=0.9)
    island_gdf.boundary.plot(ax=ax, color="#1A1A1A", linewidth=1.5)

    # Set bounds based on zoom mode and whether island extends beyond
    if zoom:
        # Zoom to island area with padding
        island_bounds = island_gdf.total_bounds
        ax.set_xlim(
            island_bounds[0] - ZOOM_PADDING_DEG,
            island_bounds[2] + ZOOM_PADDING_DEG,
        )
        ax.set_ylim(
            island_bounds[1] - ZOOM_PADDING_DEG,
            island_bounds[3] + ZOOM_PADDING_DEG,
        )
    elif extends_beyond:
        # Include the full island in view
        island_bounds = island_gdf.total_bounds
        poland_bounds = poland_boundary.total_bounds
        ax.set_xlim(
            min(poland_bounds[0], island_bounds[0] - 0.1),
            max(poland_bounds[2], island_bounds[2] + 0.1),
        )
        ax.set_ylim(
            min(poland_bounds[1], island_bounds[1] - 0.1),
            max(poland_bounds[3], island_bounds[3] + 0.1),
        )
    else:
        # Normal Poland bounds
        bounds = poland_boundary.total_bounds
        ax.set_xlim(bounds[0], bounds[2])
        ax.set_ylim(bounds[1], bounds[3])

    return fig


def generate_island_image_bytes(
    island_gdf: gpd.GeoDataFrame,
    poland_boundary: gpd.GeoDataFrame,
    *,
    zoom: bool,
) -> bytes:
    """Generate an island map image as bytes."""
    fig = create_island_map(island_gdf, poland_boundary, zoom=zoom)

    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=150)
    plt.close(fig)
    buf.seek(0)

    return buf.read()


# Global variables for multiprocessing (set via initializer)
_mp_poland_boundary: gpd.GeoDataFrame | None = None
_mp_zoom_mode: str = "no-zoom"


def _init_worker(poland_geojson: str, zoom_mode: str) -> None:
    """Initialize worker process with shared data."""
    global _mp_poland_boundary, _mp_zoom_mode  # noqa: PLW0603
    _mp_poland_boundary = gpd.read_file(poland_geojson)
    _mp_zoom_mode = zoom_mode


def _render_single_island(args: tuple[str, str]) -> tuple[str, bytes]:
    """Render a single island image (worker function).

    Args:
        args: Tuple of (island_name, island_geojson_str).

    Returns:
        Tuple of (island_name, image_bytes).
    """
    island_name, island_geojson = args
    island_gdf = gpd.read_file(island_geojson)

    assert _mp_poland_boundary is not None  # noqa: S101

    image_data = generate_island_image_bytes(
        island_gdf, _mp_poland_boundary, zoom=(_mp_zoom_mode == "zoom")
    )
    return island_name, image_data


def generate_anki_package(
    islands: gpd.GeoDataFrame,
    poland_boundary: gpd.GeoDataFrame,
    deck_name: str = "Polish Islands",
    *,
    zoom: bool = True,
) -> genanki.Package:
    """Generate Anki package for Polish islands."""
    model_id_hash = hashlib.md5(f"polish_islands_{deck_name}".encode())  # noqa: S324
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
.info-text {
    font-size: 18px;
    color: #7F8C8D;
    margin-top: 10px;
}
.card.night_mode .info-text {
    color: #BDC3C7;
}
"""

    my_model = genanki.Model(
        model_id,
        "Polish Island Model",
        fields=[
            {"name": "IslandMap"},
            {"name": "IslandName"},
            {"name": "Area"},
        ],
        templates=[
            {
                "name": "Card 1",
                "qfmt": '<div class="map-container">{{IslandMap}}</div>',
                "afmt": '<div class="map-container">{{IslandMap}}</div>'
                '<hr id="answer">'
                '<div class="answer-text">{{IslandName}}</div>'
                '<div class="info-text">{{Area}} km²</div>',
            },
        ],
        css=card_css,
    )

    deck_id = random.randrange(1 << 30, 1 << 31)  # noqa: S311
    my_deck = genanki.Deck(deck_id, deck_name)
    media_files = []

    # Prepare data for parallel processing
    with tempfile.NamedTemporaryFile(suffix=".geojson", delete=False) as f:
        poland_boundary.to_file(f.name, driver="GeoJSON")
        poland_geojson_path = f.name

    # Prepare work items: (island_name, island_geojson_str)
    work_items: list[tuple[str, str]] = []
    for _, row in islands.iterrows():
        island_gdf = gpd.GeoDataFrame([row], crs=islands.crs)
        island_geojson = island_gdf.to_json()
        work_items.append((row["name"], island_geojson))

    # Use multiprocessing for parallel rendering
    zoom_mode = "zoom" if zoom else "no-zoom"
    num_workers = min(mp.cpu_count(), 8)
    sys.stdout.write(
        f"Rendering {len(work_items)} images using {num_workers} workers...\n"
    )

    results: dict[str, bytes] = {}
    with mp.Pool(
        num_workers,
        initializer=_init_worker,
        initargs=(poland_geojson_path, zoom_mode),
    ) as pool:
        for i, (island_name, image_data) in enumerate(
            pool.imap_unordered(_render_single_island, work_items)
        ):
            results[island_name] = image_data
            if (i + 1) % 10 == 0:
                sys.stdout.write(f"  Rendered {i + 1}/{len(work_items)}...\n")

    # Clean up temp file
    Path(poland_geojson_path).unlink(missing_ok=True)

    # Create notes from results
    for _, row in islands.iterrows():
        island_name = row["name"]
        area_km2 = round(row["area_km2"], 1) if "area_km2" in row else 0
        image_data = results[island_name]
        filename = f"island_{island_name.replace(' ', '_').replace('/', '_')}.png"

        note = genanki.Note(
            model=my_model,
            fields=[f'<img src="{filename}">', island_name, str(area_km2)],
            tags=["geography", "poland", "islands", "coastal"],
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
        description="Generate Anki flashcards for Polish islands.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Output file path (default: polish_islands.apkg)",
    )
    parser.add_argument(
        "--deck-name",
        "-d",
        type=str,
        default="Polish Islands",
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
    output_path = Path(args.output) if args.output else Path("polish_islands.apkg")

    try:
        sys.stdout.write("Loading islands data...\n")
        islands = get_polish_islands()
        poland_boundary = get_poland_boundary()
        num_islands = len(islands)

        sys.stdout.write(f"Found {num_islands} islands.\n")
        sys.stdout.write("Generating flashcards...\n")

        package = generate_anki_package(islands, poland_boundary, args.deck_name)
        package.write_to_file(str(output_path))

        # Export preview images if requested
        if args.preview:
            preview_dir = Path(args.preview)
            preview_dir.mkdir(parents=True, exist_ok=True)
            preview_islands = list(islands.iterrows())[: args.preview_count]
            sys.stdout.write(
                f"Exporting {len(preview_islands)} preview images "
                f"to {preview_dir}...\n"
            )
            for _, row in preview_islands:
                island_name = row["name"]
                island_gdf = gpd.GeoDataFrame([row], crs=islands.crs)
                image_data = generate_island_image_bytes(
                    island_gdf, poland_boundary, zoom=True
                )
                safe_name = island_name.replace(" ", "_").replace("/", "_")
                preview_path = preview_dir / f"{safe_name}.png"
                preview_path.write_bytes(image_data)
                sys.stdout.write(f"  Saved: {preview_path.name}\n")

        sys.stdout.write("\n")
        sys.stdout.write("=" * 60 + "\n")
        sys.stdout.write("FLASHCARD GENERATION COMPLETE\n")
        sys.stdout.write("=" * 60 + "\n")
        sys.stdout.write(f"Islands: {num_islands}\n")
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
