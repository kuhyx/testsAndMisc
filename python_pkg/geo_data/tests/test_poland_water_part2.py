"""Tests for islands, coastal features, and UNESCO sites download paths."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import geopandas as gpd
from shapely.geometry import Polygon

from python_pkg.geo_data._poland_water import (
    get_polish_coastal_features,
    get_polish_islands,
    get_polish_unesco_sites,
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


class TestGetPolishIslands:
    """Tests for get_polish_islands."""

    @patch("python_pkg.geo_data._poland_water.gpd.read_file")
    @patch("python_pkg.geo_data._poland_water.CACHE_DIR")
    def test_cached_with_area(
        self, mock_cache_dir: MagicMock, mock_read: MagicMock
    ) -> None:
        mock_path = MagicMock()
        mock_cache_dir.__truediv__ = MagicMock(return_value=mock_path)
        mock_path.exists.return_value = True
        mock_gdf = gpd.GeoDataFrame(
            {"name": ["Wolin"], "area_km2": [265.0]},
            geometry=[_POLY],
            crs="EPSG:4326",
        )
        mock_read.return_value = mock_gdf
        result = get_polish_islands()
        assert result.iloc[0]["area_km2"] == 265.0

    @patch("python_pkg.geo_data._poland_water.gpd.read_file")
    @patch("python_pkg.geo_data._poland_water.CACHE_DIR")
    def test_cached_without_area(
        self, mock_cache_dir: MagicMock, mock_read: MagicMock
    ) -> None:
        mock_path = MagicMock()
        mock_cache_dir.__truediv__ = MagicMock(return_value=mock_path)
        mock_path.exists.return_value = True
        mock_gdf = gpd.GeoDataFrame(
            {"name": ["Wolin"]},
            geometry=[_POLY],
            crs="EPSG:4326",
        )
        mock_read.return_value = mock_gdf
        result = get_polish_islands()
        assert len(result) == 1

    @patch("python_pkg.geo_data._poland_water._add_area_column")
    @patch("python_pkg.geo_data._poland_water.gpd.GeoDataFrame.from_features")
    @patch("python_pkg.geo_data._poland_water._ensure_cache_dir")
    @patch("python_pkg.geo_data._poland_water._overpass_query")
    @patch("python_pkg.geo_data._poland_water.CACHE_DIR")
    @patch("python_pkg.geo_data._poland_water.sys.stdout")
    def test_downloads_islands(
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
                    "tags": {"name": "Wolin"},
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
                    "tags": {"name": "Wolin"},
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
            {"name": ["Wolin"]},
            geometry=[_POLY],
            crs="EPSG:4326",
        )
        mock_from_features.return_value = mock_gdf
        gdf_with_area = mock_gdf.copy()
        gdf_with_area["area_km2"] = [265.0]
        mock_add_area.return_value = gdf_with_area

        result = get_polish_islands()
        assert len(result) == 1

    @patch("python_pkg.geo_data._poland_water._add_area_column")
    @patch("python_pkg.geo_data._poland_water.gpd.GeoDataFrame.from_features")
    @patch("python_pkg.geo_data._poland_water._ensure_cache_dir")
    @patch("python_pkg.geo_data._poland_water._overpass_query")
    @patch("python_pkg.geo_data._poland_water.CACHE_DIR")
    @patch("python_pkg.geo_data._poland_water.sys.stdout")
    def test_downloads_islands_empty(
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
        result = get_polish_islands()
        assert len(result) == 0


class TestGetPolishCoastalFeatures:
    """Tests for get_polish_coastal_features."""

    @patch("python_pkg.geo_data._poland_water.gpd.read_file")
    @patch("python_pkg.geo_data._poland_water.CACHE_DIR")
    def test_cached_with_length(
        self, mock_cache_dir: MagicMock, mock_read: MagicMock
    ) -> None:
        mock_path = MagicMock()
        mock_cache_dir.__truediv__ = MagicMock(return_value=mock_path)
        mock_path.exists.return_value = True
        mock_gdf = gpd.GeoDataFrame(
            {"name": ["Mierzeja Helska"], "length_km": [35.0]},
            geometry=[_POLY],
            crs="EPSG:4326",
        )
        mock_read.return_value = mock_gdf
        result = get_polish_coastal_features()
        assert result.iloc[0]["length_km"] == 35.0

    @patch("python_pkg.geo_data._poland_water.gpd.read_file")
    @patch("python_pkg.geo_data._poland_water.CACHE_DIR")
    def test_cached_without_length(
        self, mock_cache_dir: MagicMock, mock_read: MagicMock
    ) -> None:
        mock_path = MagicMock()
        mock_cache_dir.__truediv__ = MagicMock(return_value=mock_path)
        mock_path.exists.return_value = True
        mock_gdf = gpd.GeoDataFrame(
            {"name": ["Mierzeja Helska"]},
            geometry=[_POLY],
            crs="EPSG:4326",
        )
        mock_read.return_value = mock_gdf
        result = get_polish_coastal_features()
        assert len(result) == 1

    @patch("python_pkg.geo_data._poland_water._add_length_column")
    @patch("python_pkg.geo_data._poland_water.gpd.GeoDataFrame.from_features")
    @patch("python_pkg.geo_data._poland_water._ensure_cache_dir")
    @patch("python_pkg.geo_data._poland_water._overpass_query")
    @patch("python_pkg.geo_data._poland_water.CACHE_DIR")
    @patch("python_pkg.geo_data._poland_water.sys.stdout")
    def test_downloads_coastal_features(
        self,
        mock_stdout: MagicMock,
        mock_cache_dir: MagicMock,
        mock_query: MagicMock,
        mock_ensure: MagicMock,
        mock_from_features: MagicMock,
        mock_add_length: MagicMock,
    ) -> None:
        mock_path = MagicMock()
        mock_cache_dir.__truediv__ = MagicMock(return_value=mock_path)
        mock_path.exists.return_value = False

        mock_query.return_value = {
            "elements": [
                # Peninsula (polygon type)
                {
                    "type": "way",
                    "tags": {"name": "Hel", "natural": "peninsula"},
                    "geometry": [
                        {"lon": 0, "lat": 0},
                        {"lon": 1, "lat": 0},
                        {"lon": 1, "lat": 1},
                        {"lon": 0, "lat": 1},
                    ],
                },
                # Cliff (line type)
                {
                    "type": "way",
                    "tags": {"name": "Klif Orłowski", "natural": "cliff"},
                    "geometry": [
                        {"lon": 0, "lat": 0},
                        {"lon": 1, "lat": 1},
                    ],
                },
                # Duplicate
                {
                    "type": "way",
                    "tags": {"name": "Hel", "natural": "peninsula"},
                    "geometry": [
                        {"lon": 0, "lat": 0},
                        {"lon": 1, "lat": 0},
                        {"lon": 1, "lat": 1},
                        {"lon": 0, "lat": 1},
                    ],
                },
                # No name
                {
                    "type": "way",
                    "tags": {"natural": "cliff"},
                    "geometry": [],
                },
                # Geometry fails (no geometry key)
                {
                    "type": "node",
                    "tags": {"name": "X", "natural": "cliff"},
                },
            ]
        }

        mock_gdf = gpd.GeoDataFrame(
            {"name": ["Hel", "Klif Orłowski"]},
            geometry=[_POLY, _POLY],
            crs="EPSG:4326",
        )
        mock_from_features.return_value = mock_gdf
        gdf_with_length = mock_gdf.copy()
        gdf_with_length["length_km"] = [35.0, 5.0]
        mock_add_length.return_value = gdf_with_length

        result = get_polish_coastal_features()
        assert len(result) == 2

    @patch("python_pkg.geo_data._poland_water._add_length_column")
    @patch("python_pkg.geo_data._poland_water.gpd.GeoDataFrame.from_features")
    @patch("python_pkg.geo_data._poland_water._ensure_cache_dir")
    @patch("python_pkg.geo_data._poland_water._overpass_query")
    @patch("python_pkg.geo_data._poland_water.CACHE_DIR")
    @patch("python_pkg.geo_data._poland_water.sys.stdout")
    def test_downloads_coastal_features_empty(
        self,
        mock_stdout: MagicMock,
        mock_cache_dir: MagicMock,
        mock_query: MagicMock,
        mock_ensure: MagicMock,
        mock_from_features: MagicMock,
        mock_add_length: MagicMock,
    ) -> None:
        mock_path = MagicMock()
        mock_cache_dir.__truediv__ = MagicMock(return_value=mock_path)
        mock_path.exists.return_value = False
        mock_query.return_value = {"elements": []}
        empty_gdf = gpd.GeoDataFrame({"name": [], "geometry": []})
        mock_from_features.return_value = empty_gdf
        mock_add_length.return_value = empty_gdf
        result = get_polish_coastal_features()
        assert len(result) == 0


class TestGetPolishUnescoSites:
    """Tests for get_polish_unesco_sites."""

    @patch("python_pkg.geo_data._poland_water.gpd.read_file")
    @patch("python_pkg.geo_data._poland_water.CACHE_DIR")
    def test_cached(self, mock_cache_dir: MagicMock, mock_read: MagicMock) -> None:
        mock_path = MagicMock()
        mock_cache_dir.__truediv__ = MagicMock(return_value=mock_path)
        mock_path.exists.return_value = True
        mock_gdf = MagicMock(spec=gpd.GeoDataFrame)
        mock_read.return_value = mock_gdf
        result = get_polish_unesco_sites()
        assert result is mock_gdf

    @patch("python_pkg.geo_data._poland_water.gpd.GeoDataFrame.from_features")
    @patch("python_pkg.geo_data._poland_water._ensure_cache_dir")
    @patch("python_pkg.geo_data._poland_water._overpass_query")
    @patch("python_pkg.geo_data._poland_water.CACHE_DIR")
    @patch("python_pkg.geo_data._poland_water.sys.stdout")
    def test_downloads_unesco_sites(
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
                # Node type
                {
                    "type": "node",
                    "tags": {"name": "Kopalnia Soli Wieliczka"},
                    "lon": 20.0,
                    "lat": 50.0,
                },
                # Relation type
                _make_relation_element("Stare Miasto w Krakowie"),
                # Way type with enough coords
                {
                    "type": "way",
                    "tags": {"name": "Auschwitz"},
                    "geometry": [
                        {"lon": 19, "lat": 50},
                        {"lon": 19.1, "lat": 50},
                        {"lon": 19.1, "lat": 50.1},
                        {"lon": 19, "lat": 50.1},
                    ],
                },
                # Way already closed
                {
                    "type": "way",
                    "tags": {"name": "Zamość"},
                    "geometry": [
                        {"lon": 23, "lat": 50.7},
                        {"lon": 23.1, "lat": 50.7},
                        {"lon": 23.1, "lat": 50.8},
                        {"lon": 23, "lat": 50.7},
                    ],
                },
                # Way too few coords
                {
                    "type": "way",
                    "tags": {"name": "TooShort"},
                    "geometry": [
                        {"lon": 19, "lat": 50},
                        {"lon": 19.1, "lat": 50},
                    ],
                },
                # Duplicate
                {
                    "type": "node",
                    "tags": {"name": "Kopalnia Soli Wieliczka"},
                    "lon": 20.0,
                    "lat": 50.0,
                },
                # No name
                {"type": "node", "tags": {}, "lon": 0, "lat": 0},
                # Unknown type
                {"type": "area", "tags": {"name": "Ignored"}},
                # Relation without outer rings
                _make_relation_element("NoOuter", include_outer=False),
                # Way without geometry key
                {"type": "way", "tags": {"name": "NoGeom"}},
            ]
        }

        mock_gdf = MagicMock(spec=gpd.GeoDataFrame)
        mock_from_features.return_value = mock_gdf

        result = get_polish_unesco_sites()
        assert result is mock_gdf
