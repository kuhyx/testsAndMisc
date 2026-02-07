"""Anki flashcard generator for Polish rivers.

Generates Anki-compatible flashcard decks with maps showing rivers
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
from geo_data import get_poland_boundary, get_polish_rivers

if TYPE_CHECKING:
    from collections.abc import Sequence

    from matplotlib.figure import Figure

RIVER_COLOR = "#2980B9"  # Dark blue for rivers
NEIGHBOR_COLOR = "#EAECEE"  # Light gray for neighboring areas


def create_river_map(
    river_gdf: gpd.GeoDataFrame,
    poland_boundary: gpd.GeoDataFrame,
) -> Figure:
    """Create a map showing Poland with one river highlighted.

    Rivers that extend beyond Poland show an extended view.
    """
    fig, ax = plt.subplots(figsize=(10, 12))
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_alpha(0)
    ax.patch.set_alpha(0)

    # Get Poland bounds
    poland_bounds = poland_boundary.total_bounds
    river_bounds = river_gdf.total_bounds

    # Check if river extends beyond Poland
    extends_beyond = (
        river_bounds[0] < poland_bounds[0]
        or river_bounds[1] < poland_bounds[1]
        or river_bounds[2] > poland_bounds[2]
        or river_bounds[3] > poland_bounds[3]
    )

    if extends_beyond:
        # Calculate extended bounds with some padding
        min_x = min(poland_bounds[0], river_bounds[0]) - 0.2
        min_y = min(poland_bounds[1], river_bounds[1]) - 0.2
        max_x = max(poland_bounds[2], river_bounds[2]) + 0.2
        max_y = max(poland_bounds[3], river_bounds[3]) + 0.2

        # Draw background for extended area (neighboring countries)
        ax.fill(
            [min_x, max_x, max_x, min_x, min_x],
            [min_y, min_y, max_y, max_y, min_y],
            color=NEIGHBOR_COLOR,
            alpha=0.3,
        )

    # Plot Poland as a plain gray shape
    poland_boundary.plot(ax=ax, color="#D5D8DC", alpha=0.6)
    poland_boundary.boundary.plot(ax=ax, color="#2C3E50", linewidth=1)

    # Plot the river
    river_gdf.plot(ax=ax, color=RIVER_COLOR, linewidth=3, alpha=0.9)

    if extends_beyond:
        ax.set_xlim(min_x, max_x)
        ax.set_ylim(min_y, max_y)
    else:
        # Set bounds to Poland
        ax.set_xlim(poland_bounds[0], poland_bounds[2])
        ax.set_ylim(poland_bounds[1], poland_bounds[3])

    return fig


def generate_river_image_bytes(
    river_gdf: gpd.GeoDataFrame,
    poland_boundary: gpd.GeoDataFrame,
) -> bytes:
    """Generate a river map image as bytes."""
    fig = create_river_map(river_gdf, poland_boundary)

    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=150)
    plt.close(fig)
    buf.seek(0)

    return buf.read()


# Global variables for multiprocessing (set via initializer)
_mp_poland_boundary: gpd.GeoDataFrame | None = None


def _init_worker(poland_geojson: str) -> None:
    """Initialize worker process with shared data."""
    global _mp_poland_boundary  # noqa: PLW0603
    _mp_poland_boundary = gpd.read_file(poland_geojson)


def _render_single_river(args: tuple[str, str]) -> tuple[str, bytes]:
    """Render a single river image (worker function).

    Args:
        args: Tuple of (river_name, river_geojson_str).

    Returns:
        Tuple of (river_name, image_bytes).
    """
    river_name, river_geojson = args
    river_gdf = gpd.read_file(river_geojson)

    assert _mp_poland_boundary is not None  # noqa: S101

    image_data = generate_river_image_bytes(river_gdf, _mp_poland_boundary)
    return river_name, image_data


def generate_anki_package(
    rivers: gpd.GeoDataFrame,
    poland_boundary: gpd.GeoDataFrame,
    deck_name: str = "Polish Rivers",
) -> genanki.Package:
    """Generate Anki package for Polish rivers."""
    model_id_hash = hashlib.md5(f"polish_rivers_{deck_name}".encode())  # noqa: S324
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
        "Polish River Model",
        fields=[
            {"name": "RiverMap"},
            {"name": "RiverName"},
            {"name": "Length"},
        ],
        templates=[
            {
                "name": "Card 1",
                "qfmt": '<div class="map-container">{{RiverMap}}</div>',
                "afmt": '<div class="map-container">{{RiverMap}}</div>'
                '<hr id="answer">'
                '<div class="answer-text">{{RiverName}}</div>'
                '<div class="info-text">~{{Length}} km w Polsce</div>',
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

    # Prepare work items: (river_name, river_geojson_str)
    work_items: list[tuple[str, str]] = []
    for _, row in rivers.iterrows():
        river_gdf = gpd.GeoDataFrame([row], crs=rivers.crs)
        river_geojson = river_gdf.to_json()
        work_items.append((row["name"], river_geojson))

    # Use multiprocessing for parallel rendering
    num_workers = min(mp.cpu_count(), 8)
    sys.stdout.write(
        f"Rendering {len(work_items)} images using {num_workers} workers...\n"
    )

    results: dict[str, bytes] = {}
    with mp.Pool(
        num_workers,
        initializer=_init_worker,
        initargs=(poland_geojson_path,),
    ) as pool:
        for i, (river_name, image_data) in enumerate(
            pool.imap_unordered(_render_single_river, work_items)
        ):
            results[river_name] = image_data
            if (i + 1) % 50 == 0:
                sys.stdout.write(f"  Rendered {i + 1}/{len(work_items)}...\n")

    # Clean up temp file
    Path(poland_geojson_path).unlink(missing_ok=True)

    # Create notes from results
    for _, row in rivers.iterrows():
        river_name = row["name"]
        length_km = round(row["length_km"]) if "length_km" in row else 0
        image_data = results[river_name]
        filename = f"river_{river_name.replace(' ', '_').replace('/', '_')}.png"

        note = genanki.Note(
            model=my_model,
            fields=[f'<img src="{filename}">', river_name, str(length_km)],
            tags=["geography", "poland", "rivers", "water"],
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
        description="Generate Anki flashcards for Polish rivers.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Output file path (default: polish_rivers.apkg)",
    )
    parser.add_argument(
        "--deck-name",
        "-d",
        type=str,
        default="Polish Rivers",
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
    output_path = Path(args.output) if args.output else Path("polish_rivers.apkg")

    try:
        sys.stdout.write("Loading rivers data...\n")
        rivers = get_polish_rivers()
        poland_boundary = get_poland_boundary()
        num_rivers = len(rivers)

        sys.stdout.write(f"Found {num_rivers} rivers.\n")
        sys.stdout.write("Generating flashcards...\n")

        package = generate_anki_package(rivers, poland_boundary, args.deck_name)
        package.write_to_file(str(output_path))

        # Export preview images if requested
        if args.preview:
            preview_dir = Path(args.preview)
            preview_dir.mkdir(parents=True, exist_ok=True)
            preview_rivers = list(rivers.iterrows())[: args.preview_count]
            sys.stdout.write(
                f"Exporting {len(preview_rivers)} preview images "
                f"to {preview_dir}...\n"
            )
            for _, row in preview_rivers:
                river_name = row["name"]
                river_gdf = gpd.GeoDataFrame([row], crs=rivers.crs)
                image_data = generate_river_image_bytes(river_gdf, poland_boundary)
                safe_name = river_name.replace(" ", "_").replace("/", "_")
                preview_path = preview_dir / f"{safe_name}.png"
                preview_path.write_bytes(image_data)
                sys.stdout.write(f"  Saved: {preview_path.name}\n")

        sys.stdout.write("\n")
        sys.stdout.write("=" * 60 + "\n")
        sys.stdout.write("FLASHCARD GENERATION COMPLETE\n")
        sys.stdout.write("=" * 60 + "\n")
        sys.stdout.write(f"Rivers: {num_rivers}\n")
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
