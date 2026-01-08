"""Shared geographic data module for Warsaw and Poland Anki generators.

This module handles downloading and caching geographic data from various sources:
- OpenStreetMap via Overpass API
- Geofabrik OSM extracts
- GitHub repositories with pre-processed GeoJSON

All data is cached locally to avoid repeated downloads.
"""

from __future__ import annotations

import contextlib
import json
from pathlib import Path
import shutil
import sys
import time
from typing import TYPE_CHECKING
from urllib.request import urlopen

import geopandas as gpd
import requests
from shapely.geometry import LineString, MultiLineString

if TYPE_CHECKING:
    from typing import Any

# Shared cache directory for all geo data
CACHE_DIR = Path(__file__).parent / "geo_cache"

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


def _ensure_cache_dir() -> None:
    """Create cache directory if it doesn't exist."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _query_wikidata(query: str) -> list[dict[str, Any]]:
    """Query Wikidata SPARQL endpoint.

    Args:
        query: SPARQL query string.

    Returns:
        List of result bindings.
    """
    response = requests.get(
        WIKIDATA_SPARQL,
        params={"query": query, "format": "json"},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["results"]["bindings"]


def _get_powiaty_population() -> dict[str, int]:
    """Get population data for all Polish powiaty from Wikidata.

    Returns:
        Dictionary mapping powiat name to population.
    """
    cache_path = CACHE_DIR / "powiaty_population.json"

    if cache_path.exists():
        return json.loads(cache_path.read_text())

    # Query Wikidata for all powiaty (Q247073) in Poland (Q36) with population
    # Filter to only current Polish powiaty using country=Poland filter
    query = """
    SELECT ?powiat ?powiatLabel ?population WHERE {
      ?powiat wdt:P31 wd:Q247073.
      ?powiat wdt:P17 wd:Q36.
      ?powiat wdt:P1082 ?population.
      SERVICE wikibase:label { bd:serviceParam wikibase:language "pl,en". }
    }
    ORDER BY DESC(?population)
    """

    sys.stdout.write("Fetching powiaty population data from Wikidata...\n")
    results = _query_wikidata(query)

    population_map: dict[str, int] = {}
    for item in results:
        label = item.get("powiatLabel", {}).get("value", "")
        pop = item.get("population", {}).get("value", "0")
        if label and pop:
            # Remove "powiat" prefix if present for matching
            clean_label = label.replace("powiat ", "").strip()
            with contextlib.suppress(ValueError):
                population_map[clean_label] = int(pop)

    _ensure_cache_dir()
    cache_path.write_text(json.dumps(population_map, ensure_ascii=False, indent=2))

    sys.stdout.write(f"Cached population data for {len(population_map)} powiaty.\n")
    return population_map


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
    with urlopen(url, timeout=REQUEST_TIMEOUT) as response:  # noqa: S310
        data = json.loads(response.read().decode())

    _ensure_cache_dir()
    cache_path.write_text(json.dumps(data))

    return gpd.GeoDataFrame.from_features(data["features"], crs="EPSG:4326")


# =============================================================================
# Warsaw Data
# =============================================================================


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
        Path(__file__).parent / "warsaw_districts" / "warszawa-dzielnice.geojson"
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
        Path(__file__).parent / "warsaw_districts" / "warszawa-dzielnice.geojson"
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

    return gpd.GeoDataFrame(result_rows, crs="EPSG:4326")


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


# =============================================================================
# Poland Data
# =============================================================================


def get_polish_wojewodztwa() -> gpd.GeoDataFrame:
    """Get Polish województwa (voivodeships).

    Returns:
        GeoDataFrame with województwa boundaries.
    """
    url = f"{POLSKA_GEOJSON_BASE}/wojewodztwa/wojewodztwa-min.geojson"
    cache_path = CACHE_DIR / "polish_wojewodztwa.geojson"
    return _download_github_geojson(url, cache_path)


def get_polish_powiaty() -> gpd.GeoDataFrame:
    """Get Polish powiaty (counties), sorted by population descending.

    Returns:
        GeoDataFrame with powiat boundaries and population.
    """
    url = f"{POLSKA_GEOJSON_BASE}/powiaty/powiaty-min.geojson"
    cache_path = CACHE_DIR / "polish_powiaty.geojson"
    gdf = _download_github_geojson(url, cache_path)

    # Get population data from Wikidata
    population_map = _get_powiaty_population()

    # Add population column
    def get_population(nazwa: str) -> int:
        """Match powiat name to population data."""
        if not nazwa:
            return 0
        # Remove "powiat " prefix for matching
        clean_name = nazwa.replace("powiat ", "").strip()
        # Try direct match
        if clean_name in population_map:
            return population_map[clean_name]
        # Try lowercase
        name_lower = clean_name.lower()
        for pop_name, pop in population_map.items():
            if pop_name.lower() == name_lower:
                return pop
        return 0

    gdf["population"] = gdf["nazwa"].apply(get_population)

    # Sort by population descending
    return gdf.sort_values("population", ascending=False).reset_index(drop=True)


def get_polish_gminy() -> gpd.GeoDataFrame:
    """Get Polish gminy (municipalities) from OSM.

    Returns:
        GeoDataFrame with gminy boundaries.
    """
    cache_path = CACHE_DIR / "polish_gminy.geojson"

    if cache_path.exists():
        return gpd.read_file(cache_path)

    sys.stdout.write("Fetching gminy data from OSM (this may take a while)...\n")
    # Polish gminy are admin_level=7 in OSM
    query = """
    [out:json][timeout:300];
    area["ISO3166-1"="PL"]->.pl;
    relation["boundary"="administrative"]["admin_level"="7"]["name"](area.pl);
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

    sys.stdout.write(f"Cached {len(features)} gminy.\n")
    return gpd.GeoDataFrame.from_features(features, crs="EPSG:4326")


def get_poland_boundary() -> gpd.GeoDataFrame:
    """Get Poland country boundary.

    Returns:
        GeoDataFrame with Poland boundary.
    """
    cache_path = CACHE_DIR / "poland_boundary.geojson"

    if cache_path.exists():
        return gpd.read_file(cache_path)

    # Dissolve from województwa
    woj = get_polish_wojewodztwa()
    # Fix invalid geometries with buffer(0)
    woj["geometry"] = woj["geometry"].buffer(0)
    poland = gpd.GeoDataFrame(geometry=[woj.union_all()], crs=woj.crs)

    _ensure_cache_dir()
    poland.to_file(cache_path, driver="GeoJSON")

    return poland


# =============================================================================
# Utility Functions
# =============================================================================


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
