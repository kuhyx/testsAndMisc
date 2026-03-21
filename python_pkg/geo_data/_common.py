"""Common utilities for geographic data operations.

Shared constants, API helpers, and geometry extraction functions used
across the geo_data package.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import time
from typing import TYPE_CHECKING
from urllib.request import urlopen

import geopandas as gpd
import requests
from shapely.geometry import (
    GeometryCollection,
    MultiPolygon,
    Polygon,
)

if TYPE_CHECKING:
    from typing import Any

# Parent directory of the geo_data package (i.e. python_pkg/)
_PKG_DIR = Path(__file__).resolve().parent.parent

# Shared cache directory for all geo data
CACHE_DIR = _PKG_DIR / "geo_cache"

# Overpass API endpoints (multiple for redundancy)
# Note: kumi.systems is more reliable, so it's first
OVERPASS_ENDPOINTS = [
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]

# GitHub URLs for pre-processed data
POLSKA_GEOJSON_BASE = "https://raw.githubusercontent.com/ppatrzyk/polska-geojson/master"

# Wikidata SPARQL endpoint
WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"

# Request timeout and retry settings
REQUEST_TIMEOUT = 180
MAX_RETRIES = 3
RETRY_DELAY = 5

# Data thresholds for filtering
MIN_PEAK_ELEVATION = 300  # meters
MIN_LAKE_AREA_KM2 = 0.5  # km²
MIN_RIVER_LENGTH_KM = 10  # km
MIN_LINE_COORDS = 2  # minimum coordinates for a line
MIN_RING_COORDS = 4  # minimum coordinates for a polygon ring


def _ensure_cache_dir() -> None:
    """Create cache directory if it doesn't exist."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _extract_polygonal_geometry(
    geom: Polygon | MultiPolygon | GeometryCollection,
) -> Polygon | MultiPolygon | None:
    """Extract only polygonal geometry from a geometry that may be mixed.

    Some OSM data comes as GeometryCollections containing polygons mixed with
    lines. This function extracts only the polygon/multipolygon parts.

    Args:
        geom: Input geometry (Polygon, MultiPolygon, or GeometryCollection).

    Returns:
        Polygon or MultiPolygon with only the polygonal parts, or None if empty.
    """
    if isinstance(geom, Polygon | MultiPolygon):
        return geom

    if isinstance(geom, GeometryCollection):
        polygons = [g for g in geom.geoms if isinstance(g, Polygon | MultiPolygon)]
        if not polygons:
            return None
        if len(polygons) == 1:
            return polygons[0]
        # Flatten MultiPolygons and combine all polygons
        all_polys = []
        for p in polygons:
            if isinstance(p, Polygon):
                all_polys.append(p)
            elif isinstance(p, MultiPolygon):  # pragma: no branch
                all_polys.extend(p.geoms)
        return MultiPolygon(all_polys)

    return None


def _try_single_request(
    endpoint: str, query: str
) -> tuple[dict[str, Any] | None, Exception | None]:
    """Try a single request to an endpoint.

    Args:
        endpoint: Overpass API endpoint URL.
        query: Overpass QL query string.

    Returns:
        Tuple of (result, error). One will be None.
    """
    try:
        sys.stdout.write(f"  Querying {endpoint}...\n")
        response = requests.post(
            endpoint,
            data={"data": query},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        result = response.json()
    except (requests.RequestException, requests.Timeout, ValueError) as e:
        return None, e
    else:
        # Check for valid response with elements
        if not isinstance(result, dict) or "elements" not in result:
            return None, ValueError("Invalid response format")
        return result, None


def _overpass_query(query: str) -> dict[str, Any]:
    """Execute an Overpass API query with retry logic.

    Args:
        query: Overpass QL query string.

    Returns:
        JSON response from the API.

    Raises:
        RuntimeError: If all endpoints fail.
    """
    last_error: Exception | None = None

    for endpoint in OVERPASS_ENDPOINTS:
        for attempt in range(MAX_RETRIES):
            result, error = _try_single_request(endpoint, query)
            if result is not None:
                return result
            last_error = error
            sys.stdout.write(f"  Attempt {attempt + 1} failed: {error}\n")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)

    msg = f"All Overpass API endpoints failed. Last error: {last_error}"
    raise RuntimeError(msg)


def _download_github_geojson(url: str, cache_path: Path) -> gpd.GeoDataFrame:
    """Download GeoJSON from GitHub and cache it.

    Args:
        url: URL to download from.
        cache_path: Path to cache the data.

    Returns:
        GeoDataFrame with the data.
    """
    if cache_path.exists():
        return gpd.read_file(cache_path)

    sys.stdout.write(f"Downloading from {url}...\n")
    if not url.startswith(("http://", "https://")):
        msg = f"Unsupported URL scheme: {url}"
        raise ValueError(msg)
    with urlopen(url, timeout=REQUEST_TIMEOUT) as response:
        data = json.loads(response.read().decode())

    _ensure_cache_dir()
    cache_path.write_text(json.dumps(data))

    return gpd.GeoDataFrame.from_features(data["features"], crs="EPSG:4326")


def _extract_osiedla_rings(
    element: dict[str, Any], min_coords: int
) -> tuple[list[list[tuple[float, float]]], list[list[tuple[float, float]]]]:
    """Extract outer and inner rings from an OSM relation.

    Args:
        element: OSM relation element.
        min_coords: Minimum number of coordinates for a valid ring.

    Returns:
        Tuple of (outer_rings, inner_rings).
    """
    outer_rings: list[list[tuple[float, float]]] = []
    inner_rings: list[list[tuple[float, float]]] = []

    for member in element.get("members", []):
        if "geometry" not in member:
            continue
        ring = [(p["lon"], p["lat"]) for p in member["geometry"]]
        if len(ring) < min_coords:
            continue
        # Close the ring if not closed
        if ring[0] != ring[-1]:
            ring.append(ring[0])
        if member.get("role") == "outer":
            outer_rings.append(ring)
        elif member.get("role") == "inner":
            inner_rings.append(ring)

    return outer_rings, inner_rings


def _build_osiedla_geometry(
    outer_rings: list[list[tuple[float, float]]],
    inner_rings: list[list[tuple[float, float]]],
) -> dict[str, Any]:
    """Build GeoJSON geometry from outer and inner rings.

    Args:
        outer_rings: List of outer ring coordinates.
        inner_rings: List of inner ring coordinates.

    Returns:
        GeoJSON geometry dict.
    """
    if len(outer_rings) == 1:
        return {
            "type": "Polygon",
            "coordinates": [outer_rings[0], *inner_rings],
        }
    # Multiple outer rings - create MultiPolygon
    # Each polygon in a MultiPolygon is [exterior, hole1, hole2, ...]
    return {
        "type": "MultiPolygon",
        "coordinates": [[ring] for ring in outer_rings],
    }


def _extract_polygon_from_element(
    element: dict[str, Any],
) -> dict[str, Any] | None:
    """Extract polygon geometry from an OSM relation or way element.

    Args:
        element: OSM element (relation or way).

    Returns:
        GeoJSON geometry dict, or None if extraction fails.
    """
    if element.get("type") == "relation":
        outer_rings, inner_rings = _extract_osiedla_rings(element, MIN_RING_COORDS)
        if not outer_rings:
            return None
        return _build_osiedla_geometry(outer_rings, inner_rings)

    if element.get("type") == "way" and "geometry" in element:
        coords = [(p["lon"], p["lat"]) for p in element["geometry"]]
        if len(coords) < MIN_RING_COORDS:
            return None
        if coords[0] != coords[-1]:
            coords.append(coords[0])
        return {"type": "Polygon", "coordinates": [coords]}

    return None


def _extract_line_from_way(element: dict[str, Any]) -> dict[str, Any] | None:
    """Extract line geometry from an OSM way element.

    Args:
        element: OSM way element.

    Returns:
        GeoJSON LineString geometry dict, or None if extraction fails.
    """
    if element.get("type") != "way" or "geometry" not in element:
        return None

    coords = [(p["lon"], p["lat"]) for p in element["geometry"]]
    if len(coords) < MIN_LINE_COORDS:
        return None

    return {"type": "LineString", "coordinates": coords}


def _add_area_column(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Add area_km2 column to a GeoDataFrame.

    Args:
        gdf: GeoDataFrame with polygon geometries.

    Returns:
        GeoDataFrame with area_km2 column added.
    """
    if len(gdf) == 0:
        return gdf
    gdf_proj = gdf.to_crs("EPSG:2180")  # Polish coordinate system
    gdf["area_km2"] = gdf_proj.geometry.area / 1_000_000
    return gdf


def _add_length_column(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Add length_km column to a GeoDataFrame.

    Args:
        gdf: GeoDataFrame with line geometries.

    Returns:
        GeoDataFrame with length_km column added.
    """
    if len(gdf) == 0:
        return gdf
    gdf_proj = gdf.to_crs("EPSG:2180")  # Polish coordinate system
    gdf["length_km"] = gdf_proj.geometry.length / 1000
    return gdf
