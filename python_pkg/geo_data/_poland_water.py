"""Polish water features and cultural sites.

Functions for downloading and caching data about Polish lakes, rivers,
islands, coastal features, and UNESCO World Heritage sites.
"""

from __future__ import annotations

import json
import sys
from typing import TYPE_CHECKING

import geopandas as gpd

from python_pkg.geo_data._common import (
    CACHE_DIR,
    MIN_LAKE_AREA_KM2,
    MIN_LINE_COORDS,
    MIN_RING_COORDS,
    MIN_RIVER_LENGTH_KM,
    _add_area_column,
    _add_length_column,
    _build_osiedla_geometry,
    _ensure_cache_dir,
    _extract_osiedla_rings,
    _extract_polygon_from_element,
    _overpass_query,
)

if TYPE_CHECKING:
    from typing import Any


def _extract_coastal_geometry(
    element: dict[str, Any],
    natural_type: str,
    line_types: tuple[str, ...],
) -> dict[str, Any] | None:
    """Extract geometry from a coastal feature element.

    For cliffs and beaches, returns LineString. For others, returns Polygon.

    Args:
        element: OSM element.
        natural_type: The natural= tag value.
        line_types: Tuple of natural types that should be lines.

    Returns:
        GeoJSON geometry dict, or None if extraction fails.
    """
    if element.get("type") == "relation":
        return _extract_polygon_from_element(element)

    if element.get("type") != "way" or "geometry" not in element:
        return None

    coords = [(p["lon"], p["lat"]) for p in element["geometry"]]
    if len(coords) < MIN_LINE_COORDS:
        return None

    # For cliffs and beaches, keep as linestring
    if natural_type in line_types:
        return {"type": "LineString", "coordinates": coords}

    # Otherwise try to make a polygon
    if len(coords) >= MIN_RING_COORDS:
        if coords[0] != coords[-1]:
            coords.append(coords[0])
        return {"type": "Polygon", "coordinates": [coords]}

    return None


def _extract_river_coords_from_element(
    element: dict[str, Any],
) -> list[list[tuple[float, float]]]:
    """Extract coordinate lists from a river element.

    Args:
        element: OSM element (way or relation).

    Returns:
        List of coordinate lists (line segments).
    """
    coord_lists: list[list[tuple[float, float]]] = []

    if element.get("type") == "way" and "geometry" in element:
        coords = [(p["lon"], p["lat"]) for p in element["geometry"]]
        if len(coords) >= MIN_LINE_COORDS:
            coord_lists.append(coords)
    elif element.get("type") == "relation":
        for member in element.get("members", []):
            if member.get("type") == "way" and "geometry" in member:
                coords = [(p["lon"], p["lat"]) for p in member["geometry"]]
                if len(coords) >= MIN_LINE_COORDS:
                    coord_lists.append(coords)

    return coord_lists


def get_polish_lakes() -> gpd.GeoDataFrame:
    """Get Polish lakes, sorted by area descending.

    Returns:
        GeoDataFrame with lake polygons.
    """
    cache_path = CACHE_DIR / "polish_lakes.geojson"

    if cache_path.exists():
        gdf = gpd.read_file(cache_path)
        if "area_km2" in gdf.columns:
            return gdf.sort_values("area_km2", ascending=False).reset_index(drop=True)
        return gdf

    sys.stdout.write("Fetching lakes data from OSM...\n")
    query = """
    [out:json][timeout:300];
    area["ISO3166-1"="PL"]->.pl;
    (
      relation["natural"="water"]["water"="lake"]["name"](area.pl);
      way["natural"="water"]["water"="lake"]["name"](area.pl);
    );
    out geom;
    """

    data = _overpass_query(query)

    features = []
    seen_names: set[str] = set()

    for element in data.get("elements", []):
        name = element.get("tags", {}).get("name", "")
        if not name or name in seen_names:
            continue

        geometry = _extract_polygon_from_element(element)
        if geometry is None:
            continue

        seen_names.add(name)
        features.append(
            {"type": "Feature", "properties": {"name": name}, "geometry": geometry}
        )

    _ensure_cache_dir()
    geojson = {"type": "FeatureCollection", "features": features}
    cache_path.write_text(json.dumps(geojson, ensure_ascii=False))

    sys.stdout.write(f"Cached {len(features)} lakes.\n")
    gdf = gpd.GeoDataFrame.from_features(features, crs="EPSG:4326")
    gdf = _add_area_column(gdf)

    if len(gdf) > 0:
        # Filter to lakes > MIN_LAKE_AREA_KM2 to exclude tiny ponds
        gdf = gdf[gdf["area_km2"] > MIN_LAKE_AREA_KM2]
        return gdf.sort_values("area_km2", ascending=False).reset_index(drop=True)

    return gdf


def get_polish_rivers() -> gpd.GeoDataFrame:
    """Get Polish rivers, sorted by length descending.

    Rivers with the same name but in different locations are kept separate
    by using unique IDs from OSM when available.

    Returns:
        GeoDataFrame with river linestrings.
    """
    cache_path = CACHE_DIR / "polish_rivers.geojson"

    if cache_path.exists():
        gdf = gpd.read_file(cache_path)
        if "length_km" in gdf.columns:
            return gdf.sort_values("length_km", ascending=False).reset_index(drop=True)
        return gdf

    sys.stdout.write("Fetching rivers data from OSM...\n")
    query = """
    [out:json][timeout:300];
    area["ISO3166-1"="PL"]->.pl;
    (
      relation["waterway"="river"]["name"](area.pl);
      way["waterway"="river"]["name"](area.pl);
    );
    out geom;
    """

    data = _overpass_query(query)

    # Group ways by river name AND wikidata ID (or OSM ID for uniqueness)
    # This prevents merging different rivers with the same name
    rivers_by_key: dict[str, list[list[tuple[float, float]]]] = {}
    river_names: dict[str, str] = {}  # key -> display name

    for element in data.get("elements", []):
        name = element.get("tags", {}).get("name", "")
        if not name:
            continue

        # Use wikidata ID if available, otherwise use element type+id
        wikidata = element.get("tags", {}).get("wikidata", "")
        if wikidata:
            key = f"{name}_{wikidata}"
        else:
            # Fall back to element ID for grouping related ways
            key = f"{name}_{element.get('type')}_{element.get('id')}"

        coord_lists = _extract_river_coords_from_element(element)
        if coord_lists:
            rivers_by_key.setdefault(key, []).extend(coord_lists)
            river_names[key] = name

    features = []
    for key, coord_lists in rivers_by_key.items():
        name = river_names[key]
        geometry: dict[str, Any]
        if len(coord_lists) == 1:
            geometry = {"type": "LineString", "coordinates": coord_lists[0]}
        else:
            geometry = {"type": "MultiLineString", "coordinates": coord_lists}

        features.append(
            {"type": "Feature", "properties": {"name": name}, "geometry": geometry}
        )

    _ensure_cache_dir()
    geojson = {"type": "FeatureCollection", "features": features}
    cache_path.write_text(json.dumps(geojson, ensure_ascii=False))

    sys.stdout.write(f"Cached {len(features)} rivers.\n")
    gdf = gpd.GeoDataFrame.from_features(features, crs="EPSG:4326")
    gdf = _add_length_column(gdf)

    if len(gdf) > 0:
        gdf = gdf[gdf["length_km"] > MIN_RIVER_LENGTH_KM]
        return gdf.sort_values("length_km", ascending=False).reset_index(drop=True)

    return gdf


def get_polish_islands() -> gpd.GeoDataFrame:
    """Get Polish islands, sorted by area descending.

    Returns:
        GeoDataFrame with island polygons.
    """
    cache_path = CACHE_DIR / "polish_islands.geojson"

    if cache_path.exists():
        gdf = gpd.read_file(cache_path)
        if "area_km2" in gdf.columns:
            return gdf.sort_values("area_km2", ascending=False).reset_index(drop=True)
        return gdf

    sys.stdout.write("Fetching islands data from OSM...\n")
    query = """
    [out:json][timeout:180];
    area["ISO3166-1"="PL"]->.pl;
    (
      relation["place"="island"]["name"](area.pl);
      way["place"="island"]["name"](area.pl);
      relation["place"="islet"]["name"](area.pl);
      way["place"="islet"]["name"](area.pl);
    );
    out geom;
    """

    data = _overpass_query(query)

    features = []
    seen_names: set[str] = set()

    for element in data.get("elements", []):
        name = element.get("tags", {}).get("name", "")
        if not name or name in seen_names:
            continue

        geometry = _extract_polygon_from_element(element)
        if geometry is None:
            continue

        seen_names.add(name)
        features.append(
            {"type": "Feature", "properties": {"name": name}, "geometry": geometry}
        )

    _ensure_cache_dir()
    geojson = {"type": "FeatureCollection", "features": features}
    cache_path.write_text(json.dumps(geojson, ensure_ascii=False))

    sys.stdout.write(f"Cached {len(features)} islands.\n")
    gdf = gpd.GeoDataFrame.from_features(features, crs="EPSG:4326")
    gdf = _add_area_column(gdf)

    if len(gdf) > 0:
        return gdf.sort_values("area_km2", ascending=False).reset_index(drop=True)
    return gdf


def get_polish_coastal_features() -> gpd.GeoDataFrame:
    """Get Polish coastal features (peninsulas, spits, cliffs), sorted by length.

    Returns:
        GeoDataFrame with coastal feature geometries.
    """
    cache_path = CACHE_DIR / "polish_coastal_features.geojson"

    if cache_path.exists():
        gdf = gpd.read_file(cache_path)
        if "length_km" in gdf.columns:
            return gdf.sort_values("length_km", ascending=False).reset_index(drop=True)
        return gdf

    sys.stdout.write("Fetching coastal features data from OSM...\n")
    query = """
    [out:json][timeout:180];
    area["ISO3166-1"="PL"]->.pl;
    (
      relation["natural"="peninsula"]["name"](area.pl);
      way["natural"="peninsula"]["name"](area.pl);
      relation["natural"="spit"]["name"](area.pl);
      way["natural"="spit"]["name"](area.pl);
      relation["natural"="cliff"]["name"](area.pl);
      way["natural"="cliff"]["name"](area.pl);
      relation["natural"="coastline"]["name"](area.pl);
      way["natural"="beach"]["name"](area.pl);
    );
    out geom;
    """

    data = _overpass_query(query)
    line_types = ("cliff", "beach", "coastline")

    features = []
    seen_names: set[str] = set()

    for element in data.get("elements", []):
        name = element.get("tags", {}).get("name", "")
        natural_type = element.get("tags", {}).get("natural", "")
        if not name or name in seen_names:
            continue

        geometry = _extract_coastal_geometry(element, natural_type, line_types)
        if geometry is None:
            continue

        seen_names.add(name)
        features.append(
            {
                "type": "Feature",
                "properties": {"name": name, "type": natural_type},
                "geometry": geometry,
            }
        )

    _ensure_cache_dir()
    geojson = {"type": "FeatureCollection", "features": features}
    cache_path.write_text(json.dumps(geojson, ensure_ascii=False))

    sys.stdout.write(f"Cached {len(features)} coastal features.\n")
    gdf = gpd.GeoDataFrame.from_features(features, crs="EPSG:4326")
    gdf = _add_length_column(gdf)

    if len(gdf) > 0:
        return gdf.sort_values("length_km", ascending=False).reset_index(drop=True)
    return gdf


def get_polish_unesco_sites() -> gpd.GeoDataFrame:
    """Get Polish UNESCO World Heritage Sites, sorted by inscription year.

    Returns:
        GeoDataFrame with UNESCO site geometries.
    """
    cache_path = CACHE_DIR / "polish_unesco_sites.geojson"

    if cache_path.exists():
        return gpd.read_file(cache_path)

    sys.stdout.write("Fetching UNESCO sites data from OSM...\n")
    query = """
    [out:json][timeout:180];
    area["ISO3166-1"="PL"]->.pl;
    (
      relation["heritage"="world_heritage_site"]["name"](area.pl);
      way["heritage"="world_heritage_site"]["name"](area.pl);
      node["heritage"="world_heritage_site"]["name"](area.pl);
      relation["heritage:operator"="whc"]["name"](area.pl);
      way["heritage:operator"="whc"]["name"](area.pl);
      node["heritage:operator"="whc"]["name"](area.pl);
    );
    out geom;
    """

    data = _overpass_query(query)

    features = []
    seen_names: set[str] = set()
    min_ring_coords = 4

    for element in data.get("elements", []):
        name = element.get("tags", {}).get("name", "")
        if not name or name in seen_names:
            continue

        if element.get("type") == "node":
            geometry: dict[str, Any] = {
                "type": "Point",
                "coordinates": [element["lon"], element["lat"]],
            }
        elif element.get("type") == "relation":
            outer_rings, inner_rings = _extract_osiedla_rings(element, min_ring_coords)
            if not outer_rings:
                continue
            geometry = _build_osiedla_geometry(outer_rings, inner_rings)
        elif element.get("type") == "way" and "geometry" in element:
            coords = [(p["lon"], p["lat"]) for p in element["geometry"]]
            if len(coords) < min_ring_coords:
                continue
            if coords[0] != coords[-1]:
                coords.append(coords[0])
            geometry = {"type": "Polygon", "coordinates": [coords]}
        else:
            continue

        seen_names.add(name)
        features.append(
            {"type": "Feature", "properties": {"name": name}, "geometry": geometry}
        )

    _ensure_cache_dir()
    geojson = {"type": "FeatureCollection", "features": features}
    cache_path.write_text(json.dumps(geojson, ensure_ascii=False))

    sys.stdout.write(f"Cached {len(features)} UNESCO sites.\n")
    return gpd.GeoDataFrame.from_features(features, crs="EPSG:4326")
