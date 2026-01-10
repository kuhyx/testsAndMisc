"""Anki flashcard generator for Polish coastal features.

Generates Anki-compatible flashcard decks with maps showing coastal features
(peninsulas, cliffs, beaches, etc.) highlighted on a Poland map.
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
from shapely.geometry import LineString, MultiLineString, MultiPolygon, Polygon

sys.path.insert(0, str(Path(__file__).parent.parent))
from geo_data import get_poland_boundary, get_polish_coastal_features

if TYPE_CHECKING:
    from collections.abc import Sequence

    from matplotlib.figure import Figure

FEATURE_COLOR_POLYGON = "#D4AC0D"  # Gold for polygon features
FEATURE_COLOR_LINE = "#D4AC0D"  # Gold for line features
LINE_WIDTH = 4


def create_coastal_map(
    feature_gdf: gpd.GeoDataFrame,
    poland_boundary: gpd.GeoDataFrame,
) -> Figure:
    """Create a map showing Poland with one coastal feature highlighted."""
    fig, ax = plt.subplots(figsize=(10, 12))
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_alpha(0)
    ax.patch.set_alpha(0)

    # Plot Poland as a plain gray shape
    poland_boundary.plot(ax=ax, color="#D5D8DC", alpha=0.6)
    poland_boundary.boundary.plot(ax=ax, color="#2C3E50", linewidth=1)

    # Plot the feature based on geometry type
    geom = feature_gdf.iloc[0].geometry
    if isinstance(geom, Polygon | MultiPolygon):
        feature_gdf.plot(ax=ax, color=FEATURE_COLOR_POLYGON, alpha=0.9)
        feature_gdf.boundary.plot(ax=ax, color="#1A1A1A", linewidth=3)
    elif isinstance(geom, LineString | MultiLineString):
        feature_gdf.plot(ax=ax, color=FEATURE_COLOR_LINE, linewidth=LINE_WIDTH)

    # Set bounds to Poland
    bounds = poland_boundary.total_bounds
    ax.set_xlim(bounds[0], bounds[2])
    ax.set_ylim(bounds[1], bounds[3])

    return fig


def generate_coastal_image_bytes(
    feature_gdf: gpd.GeoDataFrame,
    poland_boundary: gpd.GeoDataFrame,
) -> bytes:
    """Generate a coastal feature map image as bytes."""
    fig = create_coastal_map(feature_gdf, poland_boundary)

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


def _render_single_feature(args: tuple[str, str]) -> tuple[str, bytes]:
    """Render a single feature image (worker function).

    Args:
        args: Tuple of (feature_name, feature_geojson_str).

    Returns:
        Tuple of (feature_name, image_bytes).
    """
    feature_name, feature_geojson = args
    feature_gdf = gpd.read_file(feature_geojson)

    assert _mp_poland_boundary is not None  # noqa: S101

    image_data = generate_coastal_image_bytes(feature_gdf, _mp_poland_boundary)
    return feature_name, image_data


def generate_anki_package(
    features: gpd.GeoDataFrame,
    poland_boundary: gpd.GeoDataFrame,
    deck_name: str = "Polish Coastal Features",
) -> genanki.Package:
    """Generate Anki package for Polish coastal features."""
    model_id_hash = hashlib.md5(  # noqa: S324
        f"polish_coastal_features_{deck_name}".encode()
    )
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
        "Polish Coastal Feature Model",
        fields=[
            {"name": "FeatureMap"},
            {"name": "FeatureName"},
            {"name": "FeatureType"},
        ],
        templates=[
            {
                "name": "Card 1",
                "qfmt": '<div class="map-container">{{FeatureMap}}</div>',
                "afmt": '<div class="map-container">{{FeatureMap}}</div>'
                '<hr id="answer">'
                '<div class="answer-text">{{FeatureName}}</div>'
                '<div class="info-text">{{FeatureType}}</div>',
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

    # Prepare work items: (feature_name, feature_geojson_str)
    work_items: list[tuple[str, str]] = []
    for _, row in features.iterrows():
        feature_gdf = gpd.GeoDataFrame([row], crs=features.crs)
        feature_geojson = feature_gdf.to_json()
        work_items.append((row["name"], feature_geojson))

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
        for i, (feature_name, image_data) in enumerate(
            pool.imap_unordered(_render_single_feature, work_items)
        ):
            results[feature_name] = image_data
            if (i + 1) % 10 == 0:
                sys.stdout.write(f"  Rendered {i + 1}/{len(work_items)}...\n")

    # Clean up temp file
    Path(poland_geojson_path).unlink(missing_ok=True)

    # Create notes from results
    for _, row in features.iterrows():
        feature_name = row["name"]
        feature_type = row.get("type", "coastal feature")
        image_data = results[feature_name]
        filename = f"coastal_{feature_name.replace(' ', '_').replace('/', '_')}.png"

        note = genanki.Note(
            model=my_model,
            fields=[f'<img src="{filename}">', feature_name, feature_type],
            tags=["geography", "poland", "coastal", "baltic"],
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
        description="Generate Anki flashcards for Polish coastal features.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Output file path (default: polish_coastal_features.apkg)",
    )
    parser.add_argument(
        "--deck-name",
        "-d",
        type=str,
        default="Polish Coastal Features",
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
    output_path = (
        Path(args.output) if args.output else Path("polish_coastal_features.apkg")
    )

    try:
        sys.stdout.write("Loading coastal features data...\n")
        features = get_polish_coastal_features()
        poland_boundary = get_poland_boundary()
        num_features = len(features)

        sys.stdout.write(f"Found {num_features} coastal features.\n")
        sys.stdout.write("Generating flashcards...\n")

        package = generate_anki_package(features, poland_boundary, args.deck_name)
        package.write_to_file(str(output_path))

        # Export preview images if requested
        if args.preview:
            preview_dir = Path(args.preview)
            preview_dir.mkdir(parents=True, exist_ok=True)
            preview_features = list(features.iterrows())[: args.preview_count]
            sys.stdout.write(
                f"Exporting {len(preview_features)} preview images "
                f"to {preview_dir}...\n"
            )
            for _, row in preview_features:
                feature_name = row["name"]
                feature_gdf = gpd.GeoDataFrame([row], crs=features.crs)
                image_data = generate_coastal_image_bytes(feature_gdf, poland_boundary)
                safe_name = feature_name.replace(" ", "_").replace("/", "_")
                preview_path = preview_dir / f"{safe_name}.png"
                preview_path.write_bytes(image_data)
                sys.stdout.write(f"  Saved: {preview_path.name}\n")

        sys.stdout.write("\n")
        sys.stdout.write("=" * 60 + "\n")
        sys.stdout.write("FLASHCARD GENERATION COMPLETE\n")
        sys.stdout.write("=" * 60 + "\n")
        sys.stdout.write(f"Coastal features: {num_features}\n")
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
