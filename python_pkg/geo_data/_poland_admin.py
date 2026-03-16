"""Polish administrative boundary data.

Functions for downloading and caching Polish administrative divisions:
województwa, powiaty, gminy, and the national boundary.
Includes Wikidata integration for population data.
"""

from __future__ import annotations

import contextlib
import json
import sys
from typing import TYPE_CHECKING

import geopandas as gpd
import requests

from python_pkg.geo_data._common import (
    CACHE_DIR,
    POLSKA_GEOJSON_BASE,
    WIKIDATA_SPARQL,
    _build_osiedla_geometry,
    _download_github_geojson,
    _ensure_cache_dir,
    _extract_osiedla_rings,
    _overpass_query,
)

if TYPE_CHECKING:
    from typing import Any


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
    """Get Polish gminy (municipalities) from OSM, sorted by area descending.

    Returns:
        GeoDataFrame with gminy boundaries.
    """
    cache_path = CACHE_DIR / "polish_gminy.geojson"

    if cache_path.exists():
        gdf = gpd.read_file(cache_path)
        if "area_km2" in gdf.columns:
            return gdf.sort_values("area_km2", ascending=False).reset_index(drop=True)
        return gdf

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
    gdf = gpd.GeoDataFrame.from_features(features, crs="EPSG:4326")

    # Add area column
    from python_pkg.geo_data._common import _add_area_column

    gdf = _add_area_column(gdf)

    return gdf.sort_values("area_km2", ascending=False).reset_index(drop=True)


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
