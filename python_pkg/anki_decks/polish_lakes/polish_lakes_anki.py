"""Anki flashcard generator for Polish lakes.

Generates Anki-compatible flashcard decks with ZOOMED maps showing lakes
highlighted for better visibility.
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
from geo_data import get_poland_boundary, get_polish_lakes

if TYPE_CHECKING:
    from collections.abc import Sequence

    from matplotlib.figure import Figure

LAKE_COLOR = "#3498DB"  # Blue for lakes
ZOOM_PADDING_DEG = 0.3  # Degrees of padding around lake for zoomed view


def create_lake_map(
    lake_gdf: gpd.GeoDataFrame,
    poland_boundary: gpd.GeoDataFrame,
    *,
    zoom: bool = True,
) -> Figure:
    """Create a map showing Poland with one lake highlighted."""
    fig, ax = plt.subplots(figsize=(10, 12))
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_alpha(0)
    ax.patch.set_alpha(0)

    # Plot Poland as a plain gray shape
    poland_boundary.plot(ax=ax, color="#D5D8DC", alpha=0.6)
    poland_boundary.boundary.plot(ax=ax, color="#2C3E50", linewidth=1)

    # Plot the lake with thinner border
    lake_gdf.plot(ax=ax, color=LAKE_COLOR, alpha=0.9)
    lake_gdf.boundary.plot(ax=ax, color="#1A1A1A", linewidth=1.5)

    if zoom:
        # Zoom to lake area with padding
        bounds = lake_gdf.total_bounds
        min_x, min_y, max_x, max_y = bounds
        # Add padding
        ax.set_xlim(min_x - ZOOM_PADDING_DEG, max_x + ZOOM_PADDING_DEG)
        ax.set_ylim(min_y - ZOOM_PADDING_DEG, max_y + ZOOM_PADDING_DEG)
    else:
        # Set bounds to Poland
        bounds = poland_boundary.total_bounds
        ax.set_xlim(bounds[0], bounds[2])
        ax.set_ylim(bounds[1], bounds[3])

    return fig


def generate_lake_image_bytes(
    lake_gdf: gpd.GeoDataFrame,
    poland_boundary: gpd.GeoDataFrame,
    *,
    zoom: bool = True,
) -> bytes:
    """Generate a lake map image as bytes."""
    fig = create_lake_map(lake_gdf, poland_boundary, zoom=zoom)

    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=150)
    plt.close(fig)
    buf.seek(0)

    return buf.read()


# Global variables for multiprocessing (set via initializer)
_mp_poland_boundary: gpd.GeoDataFrame | None = None
_mp_zoom: bool = True


def _init_worker(poland_geojson: str, zoom_mode: str) -> None:
    """Initialize worker process with shared data."""
    global _mp_poland_boundary, _mp_zoom  # noqa: PLW0603
    _mp_poland_boundary = gpd.read_file(poland_geojson)
    _mp_zoom = zoom_mode == "zoom"


def _render_single_lake(args: tuple[str, str]) -> tuple[str, bytes]:
    """Render a single lake image (worker function).

    Args:
        args: Tuple of (lake_name, lake_geojson_str).

    Returns:
        Tuple of (lake_name, image_bytes).
    """
    lake_name, lake_geojson = args
    lake_gdf = gpd.read_file(lake_geojson)

    assert _mp_poland_boundary is not None  # noqa: S101

    image_data = generate_lake_image_bytes(lake_gdf, _mp_poland_boundary, zoom=_mp_zoom)
    return lake_name, image_data


def generate_anki_package(
    lakes: gpd.GeoDataFrame,
    poland_boundary: gpd.GeoDataFrame,
    deck_name: str = "Polish Lakes",
    *,
    zoom: bool = True,
) -> genanki.Package:
    """Generate Anki package for Polish lakes."""
    model_id_hash = hashlib.md5(f"polish_lakes_{deck_name}".encode())  # noqa: S324
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
        "Polish Lake Model",
        fields=[
            {"name": "LakeMap"},
            {"name": "LakeName"},
            {"name": "Area"},
        ],
        templates=[
            {
                "name": "Card 1",
                "qfmt": '<div class="map-container">{{LakeMap}}</div>',
                "afmt": '<div class="map-container">{{LakeMap}}</div>'
                '<hr id="answer">'
                '<div class="answer-text">{{LakeName}}</div>'
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

    # Prepare work items: (lake_name, lake_geojson_str)
    work_items: list[tuple[str, str]] = []
    for _, row in lakes.iterrows():
        lake_gdf = gpd.GeoDataFrame([row], crs=lakes.crs)
        lake_geojson = lake_gdf.to_json()
        work_items.append((row["name"], lake_geojson))

    # Use multiprocessing for parallel rendering
    num_workers = min(mp.cpu_count(), 8)
    sys.stdout.write(
        f"Rendering {len(work_items)} images using {num_workers} workers...\n"
    )

    results: dict[str, bytes] = {}
    with mp.Pool(
        num_workers,
        initializer=_init_worker,
        initargs=(poland_geojson_path, "zoom" if zoom else "no-zoom"),
    ) as pool:
        for i, (lake_name, image_data) in enumerate(
            pool.imap_unordered(_render_single_lake, work_items)
        ):
            results[lake_name] = image_data
            if (i + 1) % 50 == 0:
                sys.stdout.write(f"  Rendered {i + 1}/{len(work_items)}...\n")

    # Clean up temp file
    Path(poland_geojson_path).unlink(missing_ok=True)

    # Create notes from results
    for _, row in lakes.iterrows():
        lake_name = row["name"]
        area_km2 = round(row["area_km2"], 1) if "area_km2" in row else 0
        image_data = results[lake_name]
        filename = f"lake_{lake_name.replace(' ', '_').replace('/', '_')}.png"

        note = genanki.Note(
            model=my_model,
            fields=[f'<img src="{filename}">', lake_name, str(area_km2)],
            tags=["geography", "poland", "lakes", "water"],
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
        description="Generate Anki flashcards for Polish lakes.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Output file path (default: polish_lakes.apkg)",
    )
    parser.add_argument(
        "--deck-name",
        "-d",
        type=str,
        default="Polish Lakes",
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
    parser.add_argument(
        "--no-zoom",
        action="store_true",
        help="Disable zoom (show entire Poland instead of zoomed region)",
    )
    parser.add_argument(
        "--limit",
        "-l",
        type=int,
        default=None,
        help="Limit number of lakes (for testing)",
    )

    args = parser.parse_args(argv)
    output_path = Path(args.output) if args.output else Path("polish_lakes.apkg")
    zoom = not args.no_zoom

    try:
        sys.stdout.write("Loading lakes data...\n")
        lakes = get_polish_lakes()
        poland_boundary = get_poland_boundary()

        if args.limit:
            lakes = lakes.head(args.limit)
            sys.stdout.write(f"Limiting to {args.limit} lakes.\n")

        num_lakes = len(lakes)

        sys.stdout.write(f"Found {num_lakes} lakes.\n")
        sys.stdout.write(f"Zoom mode: {'enabled' if zoom else 'disabled'}\n")
        sys.stdout.write("Generating flashcards...\n")

        package = generate_anki_package(
            lakes, poland_boundary, args.deck_name, zoom=zoom
        )
        package.write_to_file(str(output_path))

        # Export preview images if requested
        if args.preview:
            preview_dir = Path(args.preview)
            preview_dir.mkdir(parents=True, exist_ok=True)
            preview_lakes = list(lakes.iterrows())[: args.preview_count]
            sys.stdout.write(
                f"Exporting {len(preview_lakes)} preview images "
                f"to {preview_dir}...\n"
            )
            for _, row in preview_lakes:
                lake_name = row["name"]
                lake_gdf = gpd.GeoDataFrame([row], crs=lakes.crs)
                image_data = generate_lake_image_bytes(
                    lake_gdf, poland_boundary, zoom=zoom
                )
                safe_name = lake_name.replace(" ", "_").replace("/", "_")
                preview_path = preview_dir / f"{safe_name}.png"
                preview_path.write_bytes(image_data)
                sys.stdout.write(f"  Saved: {preview_path.name}\n")

        sys.stdout.write("\n")
        sys.stdout.write("=" * 60 + "\n")
        sys.stdout.write("FLASHCARD GENERATION COMPLETE\n")
        sys.stdout.write("=" * 60 + "\n")
        sys.stdout.write(f"Lakes: {num_lakes}\n")
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
