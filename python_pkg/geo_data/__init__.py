"""Shared geographic data module for Warsaw and Poland Anki generators.

This module handles downloading and caching geographic data from various sources:
- OpenStreetMap via Overpass API
- Geofabrik OSM extracts
- GitHub repositories with pre-processed GeoJSON

All data is cached locally to avoid repeated downloads.
"""

from __future__ import annotations

import shutil
import sys

from python_pkg.geo_data._common import (
    CACHE_DIR,
    MAX_RETRIES,
    MIN_LAKE_AREA_KM2,
    MIN_LINE_COORDS,
    MIN_PEAK_ELEVATION,
    MIN_RING_COORDS,
    MIN_RIVER_LENGTH_KM,
    OVERPASS_ENDPOINTS,
    POLSKA_GEOJSON_BASE,
    REQUEST_TIMEOUT,
    RETRY_DELAY,
    WIKIDATA_SPARQL,
)
from python_pkg.geo_data._poland_admin import (
    get_poland_boundary,
    get_polish_gminy,
    get_polish_powiaty,
    get_polish_wojewodztwa,
)
from python_pkg.geo_data._poland_nature import (
    get_polish_forests,
    get_polish_landscape_parks,
    get_polish_mountain_peaks,
    get_polish_mountain_ranges,
    get_polish_national_parks,
    get_polish_nature_reserves,
)
from python_pkg.geo_data._poland_water import (
    get_polish_coastal_features,
    get_polish_islands,
    get_polish_lakes,
    get_polish_rivers,
    get_polish_unesco_sites,
)
from python_pkg.geo_data._warsaw import (
    get_vistula_river,
    get_warsaw_boundary,
    get_warsaw_bridges,
    get_warsaw_districts,
    get_warsaw_metro_stations,
    get_warsaw_osiedla,
)
from python_pkg.geo_data._warsaw_places import get_warsaw_landmarks, get_warsaw_streets

__all__ = [
    "CACHE_DIR",
    "MAX_RETRIES",
    "MIN_LAKE_AREA_KM2",
    "MIN_LINE_COORDS",
    "MIN_PEAK_ELEVATION",
    "MIN_RING_COORDS",
    "MIN_RIVER_LENGTH_KM",
    "OVERPASS_ENDPOINTS",
    "POLSKA_GEOJSON_BASE",
    "REQUEST_TIMEOUT",
    "RETRY_DELAY",
    "WIKIDATA_SPARQL",
    "clear_cache",
    "download_all_poland_data",
    "download_all_warsaw_data",
    "get_poland_boundary",
    "get_polish_coastal_features",
    "get_polish_forests",
    "get_polish_gminy",
    "get_polish_islands",
    "get_polish_lakes",
    "get_polish_landscape_parks",
    "get_polish_mountain_peaks",
    "get_polish_mountain_ranges",
    "get_polish_national_parks",
    "get_polish_nature_reserves",
    "get_polish_powiaty",
    "get_polish_rivers",
    "get_polish_unesco_sites",
    "get_polish_wojewodztwa",
    "get_vistula_river",
    "get_warsaw_boundary",
    "get_warsaw_bridges",
    "get_warsaw_districts",
    "get_warsaw_landmarks",
    "get_warsaw_metro_stations",
    "get_warsaw_osiedla",
    "get_warsaw_streets",
]


def download_all_warsaw_data() -> None:
    """Download and cache all Warsaw geographic data.

    Call this once to pre-populate the cache.
    """
    sys.stdout.write("Downloading all Warsaw geographic data...\n")
    sys.stdout.write("=" * 60 + "\n")

    sys.stdout.write("\n1. Warsaw boundary...\n")
    get_warsaw_boundary()

    sys.stdout.write("\n2. Vistula river...\n")
    get_vistula_river()

    sys.stdout.write("\n3. Warsaw bridges...\n")
    get_warsaw_bridges()

    sys.stdout.write("\n4. Metro stations...\n")
    get_warsaw_metro_stations()

    sys.stdout.write("\n5. Major streets...\n")
    get_warsaw_streets()

    sys.stdout.write("\n6. Landmarks...\n")
    get_warsaw_landmarks()

    sys.stdout.write("\n7. Osiedla...\n")
    get_warsaw_osiedla()

    sys.stdout.write("\n" + "=" * 60 + "\n")
    sys.stdout.write("All Warsaw data cached successfully!\n")


def download_all_poland_data() -> None:
    """Download and cache all Poland geographic data.

    Call this once to pre-populate the cache.
    """
    sys.stdout.write("Downloading all Poland geographic data...\n")
    sys.stdout.write("=" * 60 + "\n")

    sys.stdout.write("\n1. Województwa...\n")
    get_polish_wojewodztwa()

    sys.stdout.write("\n2. Powiaty...\n")
    get_polish_powiaty()

    sys.stdout.write("\n3. Gminy (this may take a while)...\n")
    get_polish_gminy()

    sys.stdout.write("\n4. Poland boundary...\n")
    get_poland_boundary()

    sys.stdout.write("\n" + "=" * 60 + "\n")
    sys.stdout.write("All Poland data cached successfully!\n")


def clear_cache() -> None:
    """Clear all cached data."""
    if CACHE_DIR.exists():
        shutil.rmtree(CACHE_DIR)
        sys.stdout.write("Cache cleared.\n")
    else:
        sys.stdout.write("Cache directory does not exist.\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Manage geographic data cache")
    parser.add_argument(
        "--download-warsaw",
        action="store_true",
        help="Download all Warsaw data",
    )
    parser.add_argument(
        "--download-poland",
        action="store_true",
        help="Download all Poland data",
    )
    parser.add_argument(
        "--download-all",
        action="store_true",
        help="Download all data",
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear cached data",
    )

    args = parser.parse_args()

    if args.clear_cache:
        clear_cache()
    elif args.download_warsaw:
        download_all_warsaw_data()
    elif args.download_poland:
        download_all_poland_data()
    elif args.download_all:
        download_all_warsaw_data()
        download_all_poland_data()
    else:
        parser.print_help()
