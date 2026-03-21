"""Warsaw streets, landmarks, and place data.

Functions for downloading and caching Warsaw streets, landmarks,
and other place-related geographic data.
"""

from __future__ import annotations

import json
import sys

import geopandas as gpd
from shapely.geometry import MultiLineString

from python_pkg.geo_data._common import CACHE_DIR, _ensure_cache_dir, _overpass_query


def get_warsaw_streets(min_length: int = 500) -> gpd.GeoDataFrame:
    """Get major Warsaw streets.

    Args:
        min_length: Minimum street length in meters.

    Returns:
        GeoDataFrame with street geometries.
    """
    cache_path = CACHE_DIR / "warsaw_streets.geojson"

    if cache_path.exists():
        gdf = gpd.read_file(cache_path)
        # Filter by length if needed
        return _filter_streets_by_length(gdf, min_length)

    sys.stdout.write("Fetching street data from OpenStreetMap...\n")
    query = """
    [out:json][timeout:120];
    area["name"="Warszawa"]["admin_level"="6"]->.warsaw;
    (
      way["highway"="primary"]["name"](area.warsaw);
      way["highway"="secondary"]["name"](area.warsaw);
      way["highway"="tertiary"]["name"](area.warsaw);
    );
    out geom;
    """

    data = _overpass_query(query)

    features = []
    min_coords = 2

    for element in data.get("elements", []):
        if element.get("type") == "way" and "geometry" in element:
            coords = [(p["lon"], p["lat"]) for p in element["geometry"]]
            if len(coords) >= min_coords:
                features.append(
                    {
                        "type": "Feature",
                        "properties": {
                            "name": element.get("tags", {}).get("name", "Unknown"),
                            "highway": element.get("tags", {}).get("highway", ""),
                        },
                        "geometry": {"type": "LineString", "coordinates": coords},
                    }
                )

    _ensure_cache_dir()
    geojson = {"type": "FeatureCollection", "features": features}
    cache_path.write_text(json.dumps(geojson))

    sys.stdout.write(f"Cached {len(features)} street segments.\n")

    gdf = gpd.GeoDataFrame.from_features(features, crs="EPSG:4326")
    return _filter_streets_by_length(gdf, min_length)


def _filter_streets_by_length(
    gdf: gpd.GeoDataFrame, min_length: int
) -> gpd.GeoDataFrame:
    """Filter and merge streets by name, keeping only those above min_length.

    Args:
        gdf: GeoDataFrame with street segments.
        min_length: Minimum length in meters.

    Returns:
        GeoDataFrame with merged streets, sorted by length (longest first).
    """
    # Group by street name
    streets: dict[str, list] = {}
    for _, row in gdf.iterrows():
        name = row.get("name", "Unknown")
        if name and name != "Unknown":
            if name not in streets:
                streets[name] = []
            streets[name].append(row.geometry)

    # Merge and filter
    result_rows = []
    for name, geometries in streets.items():
        merged = geometries[0] if len(geometries) == 1 else MultiLineString(geometries)

        # Create temp GeoDataFrame for length calculation
        temp_gdf = gpd.GeoDataFrame(geometry=[merged], crs="EPSG:4326")
        temp_proj = temp_gdf.to_crs("EPSG:2180")  # Polish coordinate system
        length = temp_proj.geometry.length.iloc[0]

        if length >= min_length:
            result_rows.append({"name": name, "geometry": merged, "length_m": length})

    # Sort by length (longest first)
    result_rows.sort(key=lambda x: x["length_m"], reverse=True)

    return gpd.GeoDataFrame(
        result_rows,
        crs="EPSG:4326" if result_rows else None,
    )


def get_warsaw_landmarks() -> gpd.GeoDataFrame:
    """Get Warsaw landmarks (museums, monuments, parks, etc.).

    Returns:
        GeoDataFrame with landmark points.
    """
    cache_path = CACHE_DIR / "warsaw_landmarks.geojson"

    if cache_path.exists():
        return gpd.read_file(cache_path)

    sys.stdout.write("Fetching landmark data...\n")
    # Simplified query - just museums and major attractions
    query = """
    [out:json][timeout:60];
    area["name"="Warszawa"]["admin_level"="6"]->.warsaw;
    (
      node["tourism"="museum"]["name"](area.warsaw);
      node["tourism"="attraction"]["name"](area.warsaw);
      node["historic"="monument"]["name"](area.warsaw);
      way["tourism"="museum"]["name"](area.warsaw);
      way["tourism"="attraction"]["name"](area.warsaw);
    );
    out center;
    """

    data = _overpass_query(query)

    features = []
    seen_names: set[str] = set()

    for element in data.get("elements", []):
        name = element.get("tags", {}).get("name", "")
        if not name or name in seen_names:
            continue

        # Get coordinates
        if element.get("type") == "node":
            lon, lat = element["lon"], element["lat"]
        elif "center" in element:
            lon, lat = element["center"]["lon"], element["center"]["lat"]
        else:
            continue

        seen_names.add(name)
        landmark_type = (
            element.get("tags", {}).get("tourism")
            or element.get("tags", {}).get("historic")
            or element.get("tags", {}).get("leisure")
            or "landmark"
        )

        features.append(
            {
                "type": "Feature",
                "properties": {"name": name, "type": landmark_type},
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
            }
        )

    _ensure_cache_dir()
    geojson = {"type": "FeatureCollection", "features": features}
    cache_path.write_text(json.dumps(geojson))

    sys.stdout.write(f"Cached {len(features)} landmarks.\n")

    if not features:
        return gpd.GeoDataFrame(
            {"name": [], "type": [], "geometry": []}, crs="EPSG:4326"
        )
    return gpd.GeoDataFrame.from_features(features, crs="EPSG:4326")
