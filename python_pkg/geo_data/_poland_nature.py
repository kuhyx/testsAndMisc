"""Polish natural land features.

Functions for downloading and caching data about Polish mountains,
national parks, forests, nature reserves, and landscape parks.
"""

from __future__ import annotations

import contextlib
import json
import sys
from typing import TYPE_CHECKING

import geopandas as gpd

from python_pkg.geo_data._common import (
    CACHE_DIR,
    MIN_PEAK_ELEVATION,
    _add_area_column,
    _build_osiedla_geometry,
    _ensure_cache_dir,
    _extract_osiedla_rings,
    _extract_polygon_from_element,
    _extract_polygonal_geometry,
    _overpass_query,
)

if TYPE_CHECKING:
    from typing import Any


def get_polish_mountain_peaks() -> gpd.GeoDataFrame:
    """Get Polish mountain peaks, sorted by elevation descending.

    Returns:
        GeoDataFrame with mountain peak points and elevation.
    """
    cache_path = CACHE_DIR / "polish_mountain_peaks.geojson"

    if cache_path.exists():
        gdf = gpd.read_file(cache_path)
        return gdf.sort_values("elevation", ascending=False).reset_index(drop=True)

    sys.stdout.write("Fetching mountain peaks data from OSM...\n")
    query = """
    [out:json][timeout:120];
    area["ISO3166-1"="PL"]->.pl;
    (
      node["natural"="peak"]["name"]["ele"](area.pl);
    );
    out;
    """

    data = _overpass_query(query)

    features = []
    seen_names: set[str] = set()

    for element in data.get("elements", []):
        if element.get("type") != "node":
            continue

        name = element.get("tags", {}).get("name", "")
        ele_str = element.get("tags", {}).get("ele", "")

        if not name or not ele_str or name in seen_names:
            continue

        with contextlib.suppress(ValueError):
            elevation = float(ele_str.replace(",", ".").split()[0])
            if elevation < MIN_PEAK_ELEVATION:
                continue

            seen_names.add(name)
            features.append(
                {
                    "type": "Feature",
                    "properties": {"name": name, "elevation": elevation},
                    "geometry": {
                        "type": "Point",
                        "coordinates": [element["lon"], element["lat"]],
                    },
                }
            )

    _ensure_cache_dir()
    geojson = {"type": "FeatureCollection", "features": features}
    cache_path.write_text(json.dumps(geojson, ensure_ascii=False))

    sys.stdout.write(f"Cached {len(features)} mountain peaks.\n")

    if not features:
        msg = "No mountain peaks found in OSM data"
        raise ValueError(msg)

    gdf = gpd.GeoDataFrame.from_features(features, crs="EPSG:4326")
    return gdf.sort_values("elevation", ascending=False).reset_index(drop=True)


def get_polish_mountain_ranges() -> gpd.GeoDataFrame:
    """Get Polish mountain ranges, sorted by area descending.

    Returns:
        GeoDataFrame with mountain range polygons.
    """
    cache_path = CACHE_DIR / "polish_mountain_ranges.geojson"

    if cache_path.exists():
        gdf = gpd.read_file(cache_path)
        # Fix invalid geometries from OSM data and extract only polygons
        gdf["geometry"] = gdf.geometry.make_valid()
        gdf["geometry"] = gdf.geometry.apply(_extract_polygonal_geometry)
        gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty]
        if "area_km2" in gdf.columns:
            return gdf.sort_values("area_km2", ascending=False).reset_index(drop=True)
        return gdf

    sys.stdout.write("Fetching mountain ranges data from OSM...\n")
    query = """
    [out:json][timeout:180];
    area["ISO3166-1"="PL"]->.pl;
    (
      relation["natural"="mountain_range"]["name"](area.pl);
      way["natural"="mountain_range"]["name"](area.pl);
    );
    out geom;
    """

    data = _overpass_query(query)

    features: list[dict[str, Any]] = []
    seen_names: set[str] = set()
    min_ring_coords = 4

    for element in data.get("elements", []):
        name = element.get("tags", {}).get("name", "")
        if not name or name in seen_names:
            continue

        if element.get("type") == "relation":
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

    sys.stdout.write(f"Cached {len(features)} mountain ranges.\n")
    gdf = gpd.GeoDataFrame.from_features(features, crs="EPSG:4326")

    # Fix invalid geometries from OSM data and extract only polygons
    gdf["geometry"] = gdf.geometry.make_valid()
    gdf["geometry"] = gdf.geometry.apply(_extract_polygonal_geometry)
    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty]

    # Calculate area in km²
    gdf_proj = gdf.to_crs("EPSG:2180")  # Polish coordinate system
    gdf["area_km2"] = gdf_proj.geometry.area / 1_000_000

    return gdf.sort_values("area_km2", ascending=False).reset_index(drop=True)


def get_polish_national_parks() -> gpd.GeoDataFrame:
    """Get all 23 Polish national parks, sorted by area descending.

    Returns:
        GeoDataFrame with national park polygons.
    """
    cache_path = CACHE_DIR / "polish_national_parks.geojson"

    if cache_path.exists():
        gdf = gpd.read_file(cache_path)
        if "area_km2" in gdf.columns:
            return gdf.sort_values("area_km2", ascending=False).reset_index(drop=True)
        return gdf

    sys.stdout.write("Fetching national parks data from OSM...\n")
    query = """
    [out:json][timeout:180];
    area["ISO3166-1"="PL"]->.pl;
    (
      relation["boundary"="national_park"]["name"](area.pl);
      relation["leisure"="nature_reserve"]["name"]["protect_class"="2"](area.pl);
    );
    out geom;
    """

    data = _overpass_query(query)

    features = []
    seen_names: set[str] = set()
    min_ring_coords = 4

    for element in data.get("elements", []):
        if element.get("type") != "relation":
            continue

        name = element.get("tags", {}).get("name", "")
        if not name or name in seen_names:
            continue

        # Filter to only include "Park Narodowy" in name
        if "Narodowy" not in name and "narodowy" not in name.lower():
            continue

        outer_rings, inner_rings = _extract_osiedla_rings(element, min_ring_coords)
        if not outer_rings:
            continue

        seen_names.add(name)
        features.append(
            {
                "type": "Feature",
                "properties": {"name": name},
                "geometry": _build_osiedla_geometry(outer_rings, inner_rings),
            }
        )

    _ensure_cache_dir()
    geojson = {"type": "FeatureCollection", "features": features}
    cache_path.write_text(json.dumps(geojson, ensure_ascii=False))

    sys.stdout.write(f"Cached {len(features)} national parks.\n")
    gdf = gpd.GeoDataFrame.from_features(features, crs="EPSG:4326")

    # Calculate area in km²
    gdf_proj = gdf.to_crs("EPSG:2180")
    gdf["area_km2"] = gdf_proj.geometry.area / 1_000_000

    return gdf.sort_values("area_km2", ascending=False).reset_index(drop=True)


def get_polish_forests() -> gpd.GeoDataFrame:
    """Get major Polish forests (puszcze), sorted by area descending.

    Returns:
        GeoDataFrame with forest polygons.
    """
    cache_path = CACHE_DIR / "polish_forests.geojson"

    if cache_path.exists():
        gdf = gpd.read_file(cache_path)
        if "area_km2" in gdf.columns:
            return gdf.sort_values("area_km2", ascending=False).reset_index(drop=True)
        return gdf

    sys.stdout.write("Fetching forests data from OSM...\n")
    # Query for named forests, especially "Puszcza" type
    query = """
    [out:json][timeout:300];
    area["ISO3166-1"="PL"]->.pl;
    (
      relation["natural"="wood"]["name"](area.pl);
      relation["landuse"="forest"]["name"~"Puszcza|Bory|Las"](area.pl);
      way["natural"="wood"]["name"~"Puszcza|Bory"](area.pl);
    );
    out geom;
    """

    data = _overpass_query(query)
    forest_keywords = ("Puszcza", "Bory", "Las ", "Lasy ")

    features = []
    seen_names: set[str] = set()

    for element in data.get("elements", []):
        name = element.get("tags", {}).get("name", "")
        if not name or name in seen_names:
            continue
        if not any(keyword in name for keyword in forest_keywords):
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

    sys.stdout.write(f"Cached {len(features)} forests.\n")
    gdf = gpd.GeoDataFrame.from_features(features, crs="EPSG:4326")
    gdf = _add_area_column(gdf)

    if len(gdf) > 0:
        return gdf.sort_values("area_km2", ascending=False).reset_index(drop=True)
    return gdf


def get_polish_nature_reserves() -> gpd.GeoDataFrame:
    """Get Polish nature reserves, sorted by area descending.

    Returns:
        GeoDataFrame with nature reserve polygons.
    """
    cache_path = CACHE_DIR / "polish_nature_reserves.geojson"

    if cache_path.exists():
        gdf = gpd.read_file(cache_path)
        if "area_km2" in gdf.columns:
            return gdf.sort_values("area_km2", ascending=False).reset_index(drop=True)
        return gdf

    sys.stdout.write(
        "Fetching nature reserves data from OSM (this may take a while)...\n"
    )
    query = """
    [out:json][timeout:600];
    area["ISO3166-1"="PL"]->.pl;
    (
      relation["leisure"="nature_reserve"]["name"](area.pl);
      way["leisure"="nature_reserve"]["name"](area.pl);
      relation["boundary"="protected_area"]["protect_class"="4"]["name"](area.pl);
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

    sys.stdout.write(f"Cached {len(features)} nature reserves.\n")
    gdf = gpd.GeoDataFrame.from_features(features, crs="EPSG:4326")
    gdf = _add_area_column(gdf)

    if len(gdf) > 0:
        return gdf.sort_values("area_km2", ascending=False).reset_index(drop=True)
    return gdf


def get_polish_landscape_parks() -> gpd.GeoDataFrame:
    """Get Polish landscape parks, sorted by area descending.

    Returns:
        GeoDataFrame with landscape park polygons.
    """
    cache_path = CACHE_DIR / "polish_landscape_parks.geojson"

    if cache_path.exists():
        gdf = gpd.read_file(cache_path)
        # Fix invalid geometries from OSM data and extract only polygons
        gdf["geometry"] = gdf.geometry.make_valid()
        gdf["geometry"] = gdf.geometry.apply(_extract_polygonal_geometry)
        # Remove any rows where geometry extraction failed
        gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty]
        if "area_km2" in gdf.columns:
            return gdf.sort_values("area_km2", ascending=False).reset_index(drop=True)
        return gdf

    sys.stdout.write("Fetching landscape parks data from OSM...\n")
    query = """
    [out:json][timeout:300];
    area["ISO3166-1"="PL"]->.pl;
    (
      relation["boundary"="protected_area"]["protect_class"="5"]["name"](area.pl);
      relation["leisure"="nature_reserve"]["name"~"Park Krajobrazowy"](area.pl);
    );
    out geom;
    """

    data = _overpass_query(query)

    features = []
    seen_names: set[str] = set()
    min_ring_coords = 4

    for element in data.get("elements", []):
        if element.get("type") != "relation":
            continue

        name = element.get("tags", {}).get("name", "")
        if not name or name in seen_names:
            continue

        outer_rings, inner_rings = _extract_osiedla_rings(element, min_ring_coords)
        if not outer_rings:
            continue

        seen_names.add(name)
        features.append(
            {
                "type": "Feature",
                "properties": {"name": name},
                "geometry": _build_osiedla_geometry(outer_rings, inner_rings),
            }
        )

    _ensure_cache_dir()
    geojson = {"type": "FeatureCollection", "features": features}
    cache_path.write_text(json.dumps(geojson, ensure_ascii=False))

    sys.stdout.write(f"Cached {len(features)} landscape parks.\n")
    gdf = gpd.GeoDataFrame.from_features(features, crs="EPSG:4326")

    # Fix invalid geometries from OSM data and extract only polygons
    gdf["geometry"] = gdf.geometry.make_valid()
    gdf["geometry"] = gdf.geometry.apply(_extract_polygonal_geometry)
    # Remove any rows where geometry extraction failed
    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty]

    if len(gdf) > 0:
        gdf_proj = gdf.to_crs("EPSG:2180")
        gdf["area_km2"] = gdf_proj.geometry.area / 1_000_000
        return gdf.sort_values("area_km2", ascending=False).reset_index(drop=True)

    return gdf
