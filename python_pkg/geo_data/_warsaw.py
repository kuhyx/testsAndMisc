"""Warsaw geographic data functions.

Functions for downloading and caching Warsaw-specific geographic data:
boundaries, districts, Vistula river, bridges, metro stations, and osiedla.
"""

from __future__ import annotations

import json
import sys

import geopandas as gpd
from shapely.geometry import LineString

from python_pkg.geo_data._common import (
    _PKG_DIR,
    CACHE_DIR,
    _build_osiedla_geometry,
    _ensure_cache_dir,
    _extract_osiedla_rings,
    _overpass_query,
)


def get_warsaw_boundary() -> gpd.GeoDataFrame:
    """Get Warsaw city boundary.

    Returns:
        GeoDataFrame with Warsaw boundary polygon.
    """
    cache_path = CACHE_DIR / "warsaw_boundary.geojson"

    if cache_path.exists():
        return gpd.read_file(cache_path)

    # Try to use districts file first
    districts_path = (
        _PKG_DIR / "anki_decks" / "warsaw_districts" / "warszawa-dzielnice.geojson"
    )
    if districts_path.exists():
        warsaw_gdf = gpd.read_file(districts_path)
        warsaw_boundary = warsaw_gdf[warsaw_gdf["name"] == "Warszawa"]
        if len(warsaw_boundary) == 0:
            warsaw_boundary = gpd.GeoDataFrame(
                geometry=[warsaw_gdf.union_all()], crs=warsaw_gdf.crs
            )
        _ensure_cache_dir()
        warsaw_boundary.to_file(cache_path, driver="GeoJSON")
        return warsaw_boundary

    # Fallback to Overpass query
    sys.stdout.write("Fetching Warsaw boundary from OpenStreetMap...\n")
    query = """
    [out:json][timeout:60];
    relation["name"="Warszawa"]["admin_level"="6"];
    out geom;
    """

    data = _overpass_query(query)

    features = []
    for element in data.get("elements", []):
        if element.get("type") == "relation":
            coords = []
            for member in element.get("members", []):
                if member.get("role") == "outer" and "geometry" in member:
                    coords.extend([(p["lon"], p["lat"]) for p in member["geometry"]])
            if coords:
                features.append(
                    {
                        "type": "Feature",
                        "properties": {"name": "Warszawa"},
                        "geometry": {"type": "Polygon", "coordinates": [coords]},
                    }
                )

    _ensure_cache_dir()
    geojson = {"type": "FeatureCollection", "features": features}
    cache_path.write_text(json.dumps(geojson))

    return gpd.GeoDataFrame.from_features(features, crs="EPSG:4326")


def get_warsaw_districts() -> gpd.GeoDataFrame:
    """Get Warsaw districts (dzielnice).

    Returns:
        GeoDataFrame with district boundaries.
    """
    districts_path = (
        _PKG_DIR / "anki_decks" / "warsaw_districts" / "warszawa-dzielnice.geojson"
    )
    if districts_path.exists():
        gdf = gpd.read_file(districts_path)
        return gdf[gdf["name"] != "Warszawa"].copy()

    msg = "Warsaw districts GeoJSON not found"
    raise FileNotFoundError(msg)


def get_vistula_river() -> gpd.GeoDataFrame:
    """Get Vistula river in Warsaw.

    Returns:
        GeoDataFrame with river geometry.
    """
    cache_path = CACHE_DIR / "warsaw_vistula.geojson"

    if cache_path.exists():
        return gpd.read_file(cache_path)

    sys.stdout.write("Fetching Vistula river data...\n")
    query = """
    [out:json][timeout:60];
    area["name"="Warszawa"]["admin_level"="6"]->.warsaw;
    (
      way["waterway"="river"]["name"="Wisła"](area.warsaw);
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
                        "properties": {"name": "Wisła"},
                        "geometry": {"type": "LineString", "coordinates": coords},
                    }
                )

    _ensure_cache_dir()
    geojson = {"type": "FeatureCollection", "features": features}
    cache_path.write_text(json.dumps(geojson))

    return gpd.GeoDataFrame.from_features(features, crs="EPSG:4326")


def get_warsaw_bridges() -> gpd.GeoDataFrame:
    """Get Warsaw bridges over the Vistula.

    Returns:
        GeoDataFrame with bridge geometries.
    """
    cache_path = CACHE_DIR / "warsaw_bridges.geojson"

    if cache_path.exists():
        return gpd.read_file(cache_path)

    sys.stdout.write("Fetching Warsaw bridges data...\n")

    # First get the Vistula to filter bridges
    vistula = get_vistula_river()
    vistula_union = vistula.union_all()
    vistula_buffer = vistula_union.buffer(0.002)  # ~200m buffer

    # Query for bridges with "Most" in name - smaller query
    query = """
    [out:json][timeout:90];
    area["name"="Warszawa"]["admin_level"="6"]->.warsaw;
    way["bridge"="yes"]["name"~"^Most"](area.warsaw);
    out geom;
    """

    data = _overpass_query(query)

    features = []
    seen_names: set[str] = set()
    min_coords = 2

    for element in data.get("elements", []):
        if element.get("type") != "way" or "geometry" not in element:
            continue

        name = element.get("tags", {}).get("name", "")
        if not name or name in seen_names:
            continue

        coords = [(p["lon"], p["lat"]) for p in element["geometry"]]
        if len(coords) < min_coords:
            continue

        line = LineString(coords)

        # Check if bridge crosses/is near Vistula
        if line.intersects(vistula_buffer):
            seen_names.add(name)
            features.append(
                {
                    "type": "Feature",
                    "properties": {"name": name, "osm_id": element.get("id")},
                    "geometry": {"type": "LineString", "coordinates": coords},
                }
            )

    # Merge segments of the same bridge
    merged_features = _merge_bridge_segments(features)

    _ensure_cache_dir()
    geojson = {"type": "FeatureCollection", "features": merged_features}
    cache_path.write_text(json.dumps(geojson))

    sys.stdout.write(f"Cached {len(merged_features)} bridges.\n")
    return gpd.GeoDataFrame.from_features(merged_features, crs="EPSG:4326")


def _merge_bridge_segments(features: list[dict]) -> list[dict]:
    """Merge bridge segments with the same name.

    Args:
        features: List of GeoJSON features.

    Returns:
        List of merged features.
    """
    by_name: dict[str, list[list[tuple[float, float]]]] = {}

    for feature in features:
        name = feature["properties"]["name"]
        coords = feature["geometry"]["coordinates"]
        if name not in by_name:
            by_name[name] = []
        by_name[name].append(coords)

    merged = []
    for name, coord_lists in by_name.items():
        if len(coord_lists) == 1:
            geom = {"type": "LineString", "coordinates": coord_lists[0]}
        else:
            geom = {"type": "MultiLineString", "coordinates": coord_lists}

        merged.append(
            {"type": "Feature", "properties": {"name": name}, "geometry": geom}
        )

    return merged


def get_warsaw_metro_stations() -> gpd.GeoDataFrame:
    """Get Warsaw metro stations with line information.

    Returns:
        GeoDataFrame with station points and line info (M1, M2, or M1/M2).
    """
    cache_path = CACHE_DIR / "warsaw_metro.geojson"

    if cache_path.exists():
        return gpd.read_file(cache_path)

    # Known stations for each line (as of 2024)
    m1_stations = {
        "Kabaty",
        "Natolin",
        "Imielin",
        "Stokłosy",
        "Ursynów",
        "Służew",
        "Wilanowska",
        "Wierzbno",
        "Racławicka",
        "Pole Mokotowskie",
        "Politechnika",
        "Centrum",
        "Świętokrzyska",  # Also M2
        "Ratusz-Arsenał",
        "Dworzec Gdański",
        "Plac Wilsona",
        "Marymont",
        "Słodowiec",
        "Stare Bielany",
        "Wawrzyszew",
        "Młociny",
    }
    m2_stations = {
        "Bródno",
        "Kondratowicza",
        "Zacisze",
        "Targówek Mieszkaniowy",
        "Trocka",
        "Szwedzka",
        "Dworzec Wileński",
        "Świętokrzyska",  # Also M1
        "Nowy Świat-Uniwersytet",
        "Centrum Nauki Kopernik",
        "Stadion Narodowy",
        "Rondo ONZ",
        "Rondo Daszyńskiego",
        "Płocka",
        "Młynów",
        "Księcia Janusza",
        "Ulrychów",
        "Bemowo",
    }

    sys.stdout.write("Fetching metro station data...\n")
    query = """
    [out:json][timeout:60];
    area["name"="Warszawa"]["admin_level"="6"]->.warsaw;
    (
      node["railway"="station"]["station"="subway"](area.warsaw);
      node["railway"="station"]["network"~"Metro"](area.warsaw);
    );
    out body;
    """

    data = _overpass_query(query)

    features = []
    seen_names: set[str] = set()

    for element in data.get("elements", []):
        if element.get("type") == "node":
            name = element.get("tags", {}).get("name", "")
            if name and name not in seen_names:
                seen_names.add(name)
                # Determine line from known station lists
                in_m1 = name in m1_stations
                in_m2 = name in m2_stations
                if in_m1 and in_m2:
                    line = "M1/M2"
                elif in_m1:
                    line = "M1"
                elif in_m2:
                    line = "M2"
                else:
                    line = "?"  # Unknown station

                features.append(
                    {
                        "type": "Feature",
                        "properties": {
                            "name": name,
                            "line": line,
                        },
                        "geometry": {
                            "type": "Point",
                            "coordinates": [element["lon"], element["lat"]],
                        },
                    }
                )

    _ensure_cache_dir()
    geojson = {"type": "FeatureCollection", "features": features}
    cache_path.write_text(json.dumps(geojson))

    sys.stdout.write(f"Cached {len(features)} metro stations.\n")
    return gpd.GeoDataFrame.from_features(features, crs="EPSG:4326")


def get_warsaw_osiedla() -> gpd.GeoDataFrame:
    """Get Warsaw osiedla (neighborhoods).

    Returns:
        GeoDataFrame with osiedla boundaries.
    """
    cache_path = CACHE_DIR / "warsaw_osiedla.geojson"

    if cache_path.exists():
        return gpd.read_file(cache_path)

    sys.stdout.write("Fetching osiedla data...\n")
    query = """
    [out:json][timeout:180];
    area["name"="Warszawa"]["admin_level"="6"]->.warsaw;
    relation["boundary"="administrative"]["admin_level"="11"]["name"](area.warsaw);
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
    cache_path.write_text(json.dumps(geojson))

    sys.stdout.write(f"Cached {len(features)} osiedla.\n")
    return gpd.GeoDataFrame.from_features(features, crs="EPSG:4326")
