"""Tests for forests, nature reserves, and landscape parks download paths."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import geopandas as gpd
from shapely.geometry import Polygon

from python_pkg.geo_data._poland_nature import (
    get_polish_forests,
    get_polish_landscape_parks,
    get_polish_nature_reserves,
)


def _make_relation_element(name: str, *, include_outer: bool = True) -> dict[str, Any]:
    """Create a mock OSM relation element."""
    members = []
    if include_outer:
        members.append(
            {
                "role": "outer",
                "geometry": [
                    {"lon": 0, "lat": 0},
                    {"lon": 1, "lat": 0},
                    {"lon": 1, "lat": 1},
                    {"lon": 0, "lat": 1},
                ],
            }
        )
    return {"type": "relation", "tags": {"name": name}, "members": members}


_POLY = Polygon([(20, 50), (21, 50), (21, 51), (20, 51)])


class TestGetPolishForests:
    """Tests for get_polish_forests."""

    @patch("python_pkg.geo_data._poland_nature.gpd.read_file")
    @patch("python_pkg.geo_data._poland_nature.CACHE_DIR")
    def test_cached_with_area(
        self, mock_cache_dir: MagicMock, mock_read: MagicMock
    ) -> None:
        mock_path = MagicMock()
        mock_cache_dir.__truediv__ = MagicMock(return_value=mock_path)
        mock_path.exists.return_value = True
        mock_gdf = gpd.GeoDataFrame(
            {"name": ["Puszcza Białowieska"], "area_km2": [600.0]},
            geometry=[_POLY],
            crs="EPSG:4326",
        )
        mock_read.return_value = mock_gdf
        result = get_polish_forests()
        assert result.iloc[0]["area_km2"] == 600.0

    @patch("python_pkg.geo_data._poland_nature.gpd.read_file")
    @patch("python_pkg.geo_data._poland_nature.CACHE_DIR")
    def test_cached_without_area(
        self, mock_cache_dir: MagicMock, mock_read: MagicMock
    ) -> None:
        mock_path = MagicMock()
        mock_cache_dir.__truediv__ = MagicMock(return_value=mock_path)
        mock_path.exists.return_value = True
        mock_gdf = gpd.GeoDataFrame(
            {"name": ["Puszcza Białowieska"]},
            geometry=[_POLY],
            crs="EPSG:4326",
        )
        mock_read.return_value = mock_gdf
        result = get_polish_forests()
        assert len(result) == 1

    @patch("python_pkg.geo_data._poland_nature._add_area_column")
    @patch("python_pkg.geo_data._poland_nature.gpd.GeoDataFrame.from_features")
    @patch("python_pkg.geo_data._poland_nature._ensure_cache_dir")
    @patch("python_pkg.geo_data._poland_nature._overpass_query")
    @patch("python_pkg.geo_data._poland_nature.CACHE_DIR")
    @patch("python_pkg.geo_data._poland_nature.sys.stdout")
    def test_downloads_forests(
        self,
        mock_stdout: MagicMock,
        mock_cache_dir: MagicMock,
        mock_query: MagicMock,
        mock_ensure: MagicMock,
        mock_from_features: MagicMock,
        mock_add_area: MagicMock,
    ) -> None:
        mock_path = MagicMock()
        mock_cache_dir.__truediv__ = MagicMock(return_value=mock_path)
        mock_path.exists.return_value = False

        mock_query.return_value = {
            "elements": [
                # Valid forest with keyword
                {
                    "type": "way",
                    "tags": {"name": "Puszcza Białowieska"},
                    "geometry": [
                        {"lon": 0, "lat": 0},
                        {"lon": 1, "lat": 0},
                        {"lon": 1, "lat": 1},
                        {"lon": 0, "lat": 1},
                    ],
                },
                # Bory keyword
                {
                    "type": "way",
                    "tags": {"name": "Bory Tucholskie"},
                    "geometry": [
                        {"lon": 2, "lat": 2},
                        {"lon": 3, "lat": 2},
                        {"lon": 3, "lat": 3},
                        {"lon": 2, "lat": 3},
                    ],
                },
                # No forest keyword -> skip
                {
                    "type": "way",
                    "tags": {"name": "Random Wood"},
                    "geometry": [
                        {"lon": 0, "lat": 0},
                        {"lon": 1, "lat": 0},
                        {"lon": 1, "lat": 1},
                        {"lon": 0, "lat": 1},
                    ],
                },
                # Duplicate
                {
                    "type": "way",
                    "tags": {"name": "Puszcza Białowieska"},
                    "geometry": [
                        {"lon": 0, "lat": 0},
                        {"lon": 1, "lat": 0},
                        {"lon": 1, "lat": 1},
                        {"lon": 0, "lat": 1},
                    ],
                },
                # No name
                {"type": "way", "tags": {}, "geometry": []},
                # Geometry extraction fails (too few coords)
                {
                    "type": "way",
                    "tags": {"name": "Las Mały"},
                    "geometry": [{"lon": 0, "lat": 0}],
                },
            ]
        }

        mock_gdf = gpd.GeoDataFrame(
            {"name": ["Puszcza Białowieska", "Bory Tucholskie"]},
            geometry=[_POLY, _POLY],
            crs="EPSG:4326",
        )
        mock_from_features.return_value = mock_gdf
        gdf_with_area = mock_gdf.copy()
        gdf_with_area["area_km2"] = [600.0, 300.0]
        mock_add_area.return_value = gdf_with_area

        result = get_polish_forests()
        assert len(result) == 2

    @patch("python_pkg.geo_data._poland_nature._add_area_column")
    @patch("python_pkg.geo_data._poland_nature.gpd.GeoDataFrame.from_features")
    @patch("python_pkg.geo_data._poland_nature._ensure_cache_dir")
    @patch("python_pkg.geo_data._poland_nature._overpass_query")
    @patch("python_pkg.geo_data._poland_nature.CACHE_DIR")
    @patch("python_pkg.geo_data._poland_nature.sys.stdout")
    def test_downloads_forests_empty(
        self,
        mock_stdout: MagicMock,
        mock_cache_dir: MagicMock,
        mock_query: MagicMock,
        mock_ensure: MagicMock,
        mock_from_features: MagicMock,
        mock_add_area: MagicMock,
    ) -> None:
        mock_path = MagicMock()
        mock_cache_dir.__truediv__ = MagicMock(return_value=mock_path)
        mock_path.exists.return_value = False
        mock_query.return_value = {"elements": []}
        empty_gdf = gpd.GeoDataFrame({"name": [], "geometry": []})
        mock_from_features.return_value = empty_gdf
        mock_add_area.return_value = empty_gdf
        result = get_polish_forests()
        assert len(result) == 0


class TestGetPolishNatureReserves:
    """Tests for get_polish_nature_reserves."""

    @patch("python_pkg.geo_data._poland_nature.gpd.read_file")
    @patch("python_pkg.geo_data._poland_nature.CACHE_DIR")
    def test_cached_with_area(
        self, mock_cache_dir: MagicMock, mock_read: MagicMock
    ) -> None:
        mock_path = MagicMock()
        mock_cache_dir.__truediv__ = MagicMock(return_value=mock_path)
        mock_path.exists.return_value = True
        mock_gdf = gpd.GeoDataFrame(
            {"name": ["Rezerwat X"], "area_km2": [50.0]},
            geometry=[_POLY],
            crs="EPSG:4326",
        )
        mock_read.return_value = mock_gdf
        result = get_polish_nature_reserves()
        assert result.iloc[0]["area_km2"] == 50.0

    @patch("python_pkg.geo_data._poland_nature.gpd.read_file")
    @patch("python_pkg.geo_data._poland_nature.CACHE_DIR")
    def test_cached_without_area(
        self, mock_cache_dir: MagicMock, mock_read: MagicMock
    ) -> None:
        mock_path = MagicMock()
        mock_cache_dir.__truediv__ = MagicMock(return_value=mock_path)
        mock_path.exists.return_value = True
        mock_gdf = gpd.GeoDataFrame(
            {"name": ["Rezerwat X"]},
            geometry=[_POLY],
            crs="EPSG:4326",
        )
        mock_read.return_value = mock_gdf
        result = get_polish_nature_reserves()
        assert len(result) == 1

    @patch("python_pkg.geo_data._poland_nature._add_area_column")
    @patch("python_pkg.geo_data._poland_nature.gpd.GeoDataFrame.from_features")
    @patch("python_pkg.geo_data._poland_nature._ensure_cache_dir")
    @patch("python_pkg.geo_data._poland_nature._overpass_query")
    @patch("python_pkg.geo_data._poland_nature.CACHE_DIR")
    @patch("python_pkg.geo_data._poland_nature.sys.stdout")
    def test_downloads_reserves(
        self,
        mock_stdout: MagicMock,
        mock_cache_dir: MagicMock,
        mock_query: MagicMock,
        mock_ensure: MagicMock,
        mock_from_features: MagicMock,
        mock_add_area: MagicMock,
    ) -> None:
        mock_path = MagicMock()
        mock_cache_dir.__truediv__ = MagicMock(return_value=mock_path)
        mock_path.exists.return_value = False

        mock_query.return_value = {
            "elements": [
                {
                    "type": "way",
                    "tags": {"name": "Rezerwat A"},
                    "geometry": [
                        {"lon": 0, "lat": 0},
                        {"lon": 1, "lat": 0},
                        {"lon": 1, "lat": 1},
                        {"lon": 0, "lat": 1},
                    ],
                },
                # Duplicate
                {
                    "type": "way",
                    "tags": {"name": "Rezerwat A"},
                    "geometry": [
                        {"lon": 0, "lat": 0},
                        {"lon": 1, "lat": 0},
                        {"lon": 1, "lat": 1},
                        {"lon": 0, "lat": 1},
                    ],
                },
                # No name
                {"type": "way", "tags": {}, "geometry": []},
                # Geometry fails
                {
                    "type": "way",
                    "tags": {"name": "Tiny"},
                    "geometry": [{"lon": 0, "lat": 0}],
                },
            ]
        }

        mock_gdf = gpd.GeoDataFrame(
            {"name": ["Rezerwat A"]},
            geometry=[_POLY],
            crs="EPSG:4326",
        )
        mock_from_features.return_value = mock_gdf
        gdf_with_area = mock_gdf.copy()
        gdf_with_area["area_km2"] = [50.0]
        mock_add_area.return_value = gdf_with_area

        result = get_polish_nature_reserves()
        assert len(result) == 1

    @patch("python_pkg.geo_data._poland_nature._add_area_column")
    @patch("python_pkg.geo_data._poland_nature.gpd.GeoDataFrame.from_features")
    @patch("python_pkg.geo_data._poland_nature._ensure_cache_dir")
    @patch("python_pkg.geo_data._poland_nature._overpass_query")
    @patch("python_pkg.geo_data._poland_nature.CACHE_DIR")
    @patch("python_pkg.geo_data._poland_nature.sys.stdout")
    def test_downloads_reserves_empty(
        self,
        mock_stdout: MagicMock,
        mock_cache_dir: MagicMock,
        mock_query: MagicMock,
        mock_ensure: MagicMock,
        mock_from_features: MagicMock,
        mock_add_area: MagicMock,
    ) -> None:
        mock_path = MagicMock()
        mock_cache_dir.__truediv__ = MagicMock(return_value=mock_path)
        mock_path.exists.return_value = False
        mock_query.return_value = {"elements": []}
        empty_gdf = gpd.GeoDataFrame({"name": [], "geometry": []})
        mock_from_features.return_value = empty_gdf
        mock_add_area.return_value = empty_gdf
        result = get_polish_nature_reserves()
        assert len(result) == 0


class TestGetPolishLandscapeParks:
    """Tests for get_polish_landscape_parks."""

    @patch("python_pkg.geo_data._poland_nature.gpd.read_file")
    @patch("python_pkg.geo_data._poland_nature.CACHE_DIR")
    def test_cached_with_area(
        self,
        mock_cache_dir: MagicMock,
        mock_read: MagicMock,
    ) -> None:
        mock_path = MagicMock()
        mock_cache_dir.__truediv__ = MagicMock(return_value=mock_path)
        mock_path.exists.return_value = True
        mock_gdf = gpd.GeoDataFrame(
            {"name": ["Park Krajobrazowy X"], "area_km2": [100.0]},
            geometry=[_POLY],
            crs="EPSG:4326",
        )
        mock_read.return_value = mock_gdf
        result = get_polish_landscape_parks()
        assert result.iloc[0]["area_km2"] == 100.0

    @patch("python_pkg.geo_data._poland_nature.gpd.read_file")
    @patch("python_pkg.geo_data._poland_nature.CACHE_DIR")
    def test_cached_without_area(
        self,
        mock_cache_dir: MagicMock,
        mock_read: MagicMock,
    ) -> None:
        mock_path = MagicMock()
        mock_cache_dir.__truediv__ = MagicMock(return_value=mock_path)
        mock_path.exists.return_value = True
        mock_gdf = gpd.GeoDataFrame(
            {"name": ["Park Krajobrazowy X"]},
            geometry=[_POLY],
            crs="EPSG:4326",
        )
        mock_read.return_value = mock_gdf
        result = get_polish_landscape_parks()
        assert len(result) == 1

    @patch("python_pkg.geo_data._poland_nature.gpd.GeoDataFrame.from_features")
    @patch("python_pkg.geo_data._poland_nature._ensure_cache_dir")
    @patch("python_pkg.geo_data._poland_nature._overpass_query")
    @patch("python_pkg.geo_data._poland_nature.CACHE_DIR")
    @patch("python_pkg.geo_data._poland_nature.sys.stdout")
    def test_downloads_landscape_parks(
        self,
        mock_stdout: MagicMock,
        mock_cache_dir: MagicMock,
        mock_query: MagicMock,
        mock_ensure: MagicMock,
        mock_from_features: MagicMock,
    ) -> None:
        mock_path = MagicMock()
        mock_cache_dir.__truediv__ = MagicMock(return_value=mock_path)
        mock_path.exists.return_value = False

        mock_query.return_value = {
            "elements": [
                _make_relation_element("Park Krajobrazowy A"),
                # Not a relation -> skip
                {
                    "type": "way",
                    "tags": {"name": "Park Krajobrazowy B"},
                    "geometry": [],
                },
                # No name
                {"type": "relation", "tags": {}, "members": []},
                # Duplicate
                _make_relation_element("Park Krajobrazowy A"),
                # No outer rings
                _make_relation_element("Park Empty", include_outer=False),
            ]
        }

        mock_gdf = gpd.GeoDataFrame(
            {"name": ["Park Krajobrazowy A"]},
            geometry=[_POLY],
            crs="EPSG:4326",
        )
        mock_from_features.return_value = mock_gdf

        result = get_polish_landscape_parks()
        assert len(result) == 1

    @patch("python_pkg.geo_data._poland_nature.gpd.GeoDataFrame.from_features")
    @patch("python_pkg.geo_data._poland_nature._ensure_cache_dir")
    @patch("python_pkg.geo_data._poland_nature._overpass_query")
    @patch("python_pkg.geo_data._poland_nature.CACHE_DIR")
    @patch("python_pkg.geo_data._poland_nature.sys.stdout")
    def test_downloads_landscape_parks_empty(
        self,
        mock_stdout: MagicMock,
        mock_cache_dir: MagicMock,
        mock_query: MagicMock,
        mock_ensure: MagicMock,
        mock_from_features: MagicMock,
    ) -> None:
        mock_path = MagicMock()
        mock_cache_dir.__truediv__ = MagicMock(return_value=mock_path)
        mock_path.exists.return_value = False
        mock_query.return_value = {"elements": []}
        empty_gdf = gpd.GeoDataFrame({"name": [], "geometry": []})
        mock_from_features.return_value = empty_gdf
        result = get_polish_landscape_parks()
        assert len(result) == 0
