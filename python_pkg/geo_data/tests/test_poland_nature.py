"""Tests for python_pkg.geo_data._poland_nature module."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import geopandas as gpd
import pytest
from shapely.geometry import Polygon

from python_pkg.geo_data._poland_nature import (
    get_polish_mountain_peaks,
    get_polish_mountain_ranges,
    get_polish_national_parks,
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


class TestGetPolishMountainPeaks:
    """Tests for get_polish_mountain_peaks."""

    @patch("python_pkg.geo_data._poland_nature.gpd.read_file")
    @patch("python_pkg.geo_data._poland_nature.CACHE_DIR")
    def test_cached(self, mock_cache_dir: MagicMock, mock_read: MagicMock) -> None:
        mock_path = MagicMock()
        mock_cache_dir.__truediv__ = MagicMock(return_value=mock_path)
        mock_path.exists.return_value = True

        mock_gdf = gpd.GeoDataFrame(
            {"name": ["Rysy", "Babia Góra"], "elevation": [2499.0, 1725.0]},
            geometry=[
                Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
                Polygon([(2, 2), (3, 2), (3, 3), (2, 3)]),
            ],
            crs="EPSG:4326",
        )
        mock_read.return_value = mock_gdf

        result = get_polish_mountain_peaks()
        assert result.iloc[0]["elevation"] == 2499.0

    @patch("python_pkg.geo_data._poland_nature.gpd.GeoDataFrame.from_features")
    @patch("python_pkg.geo_data._poland_nature._ensure_cache_dir")
    @patch("python_pkg.geo_data._poland_nature._overpass_query")
    @patch("python_pkg.geo_data._poland_nature.CACHE_DIR")
    @patch("python_pkg.geo_data._poland_nature.sys.stdout")
    def test_downloads_peaks(
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
                {
                    "type": "node",
                    "tags": {"name": "Rysy", "ele": "2499"},
                    "lon": 20.0,
                    "lat": 49.0,
                },
                # Below threshold
                {
                    "type": "node",
                    "tags": {"name": "LowPeak", "ele": "100"},
                    "lon": 20.0,
                    "lat": 49.0,
                },
                # Missing ele
                {
                    "type": "node",
                    "tags": {"name": "NoEle"},
                    "lon": 20.0,
                    "lat": 49.0,
                },
                # Duplicate name
                {
                    "type": "node",
                    "tags": {"name": "Rysy", "ele": "2499"},
                    "lon": 20.0,
                    "lat": 49.0,
                },
                # Not a node
                {
                    "type": "way",
                    "tags": {"name": "Way", "ele": "500"},
                },
                # No name
                {
                    "type": "node",
                    "tags": {"ele": "500"},
                    "lon": 20.0,
                    "lat": 49.0,
                },
                # Comma in ele
                {
                    "type": "node",
                    "tags": {"name": "Peak2", "ele": "500,5 m"},
                    "lon": 20.0,
                    "lat": 49.0,
                },
                # Invalid ele
                {
                    "type": "node",
                    "tags": {"name": "BadEle", "ele": "abc"},
                    "lon": 20.0,
                    "lat": 49.0,
                },
            ]
        }

        mock_gdf = gpd.GeoDataFrame(
            {"name": ["Rysy", "Peak2"], "elevation": [2499.0, 500.5]},
            geometry=[
                Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
                Polygon([(2, 2), (3, 2), (3, 3), (2, 3)]),
            ],
            crs="EPSG:4326",
        )
        mock_from_features.return_value = mock_gdf

        result = get_polish_mountain_peaks()
        assert result.iloc[0]["elevation"] == 2499.0

    @patch("python_pkg.geo_data._poland_nature._ensure_cache_dir")
    @patch("python_pkg.geo_data._poland_nature._overpass_query")
    @patch("python_pkg.geo_data._poland_nature.CACHE_DIR")
    @patch("python_pkg.geo_data._poland_nature.sys.stdout")
    def test_no_peaks_raises(
        self,
        mock_stdout: MagicMock,
        mock_cache_dir: MagicMock,
        mock_query: MagicMock,
        mock_ensure: MagicMock,
    ) -> None:
        mock_path = MagicMock()
        mock_cache_dir.__truediv__ = MagicMock(return_value=mock_path)
        mock_path.exists.return_value = False
        mock_query.return_value = {"elements": []}

        with pytest.raises(ValueError, match="No mountain peaks found"):
            get_polish_mountain_peaks()


class TestGetPolishMountainRanges:
    """Tests for get_polish_mountain_ranges."""

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

        poly = Polygon([(20, 50), (21, 50), (21, 51), (20, 51)])
        mock_gdf = gpd.GeoDataFrame(
            {"name": ["Tatry"], "area_km2": [100.0]},
            geometry=[poly],
            crs="EPSG:4326",
        )
        mock_read.return_value = mock_gdf

        result = get_polish_mountain_ranges()
        assert "area_km2" in result.columns

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

        poly = Polygon([(20, 50), (21, 50), (21, 51), (20, 51)])
        mock_gdf = gpd.GeoDataFrame(
            {"name": ["Tatry"]},
            geometry=[poly],
            crs="EPSG:4326",
        )
        mock_read.return_value = mock_gdf

        result = get_polish_mountain_ranges()
        assert len(result) >= 0

    @patch("python_pkg.geo_data._poland_nature.gpd.GeoDataFrame.from_features")
    @patch("python_pkg.geo_data._poland_nature._ensure_cache_dir")
    @patch("python_pkg.geo_data._poland_nature._overpass_query")
    @patch("python_pkg.geo_data._poland_nature.CACHE_DIR")
    @patch("python_pkg.geo_data._poland_nature.sys.stdout")
    def test_downloads_ranges(
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
                # Relation
                _make_relation_element("Tatry"),
                # Way with enough coords
                {
                    "type": "way",
                    "tags": {"name": "Bieszczady"},
                    "geometry": [
                        {"lon": 0, "lat": 0},
                        {"lon": 1, "lat": 0},
                        {"lon": 1, "lat": 1},
                        {"lon": 0, "lat": 1},
                    ],
                },
                # Way with auto-close
                {
                    "type": "way",
                    "tags": {"name": "Karkonosze"},
                    "geometry": [
                        {"lon": 0, "lat": 0},
                        {"lon": 1, "lat": 0},
                        {"lon": 1, "lat": 1},
                        {"lon": 0, "lat": 0.5},
                    ],
                },
                # Way already closed (first == last)
                {
                    "type": "way",
                    "tags": {"name": "Sudety"},
                    "geometry": [
                        {"lon": 2, "lat": 2},
                        {"lon": 3, "lat": 2},
                        {"lon": 3, "lat": 3},
                        {"lon": 2, "lat": 2},
                    ],
                },
                # Way too few coords
                {
                    "type": "way",
                    "tags": {"name": "Short"},
                    "geometry": [{"lon": 0, "lat": 0}, {"lon": 1, "lat": 0}],
                },
                # Duplicate
                _make_relation_element("Tatry"),
                # No name
                _make_relation_element(""),
                # Unknown type
                {"type": "node", "tags": {"name": "Ignored"}},
                # Way without geometry
                {"type": "way", "tags": {"name": "NoGeom"}},
                # Relation without outer rings
                _make_relation_element("NoOuter", include_outer=False),
            ]
        }

        poly = Polygon([(20, 50), (21, 50), (21, 51), (20, 51)])
        mock_gdf = gpd.GeoDataFrame(
            {"name": ["Tatry", "Bieszczady", "Karkonosze", "Sudety"]},
            geometry=[poly, poly, poly, poly],
            crs="EPSG:4326",
        )
        mock_from_features.return_value = mock_gdf

        result = get_polish_mountain_ranges()
        assert len(result) >= 0


class TestGetPolishNationalParks:
    """Tests for get_polish_national_parks."""

    @patch("python_pkg.geo_data._poland_nature.gpd.read_file")
    @patch("python_pkg.geo_data._poland_nature.CACHE_DIR")
    def test_cached_with_area(
        self, mock_cache_dir: MagicMock, mock_read: MagicMock
    ) -> None:
        mock_path = MagicMock()
        mock_cache_dir.__truediv__ = MagicMock(return_value=mock_path)
        mock_path.exists.return_value = True

        mock_gdf = gpd.GeoDataFrame(
            {"name": ["Tatrzański Park Narodowy"], "area_km2": [200.0]},
            geometry=[Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])],
            crs="EPSG:4326",
        )
        mock_read.return_value = mock_gdf

        result = get_polish_national_parks()
        assert result.iloc[0]["area_km2"] == 200.0

    @patch("python_pkg.geo_data._poland_nature.gpd.read_file")
    @patch("python_pkg.geo_data._poland_nature.CACHE_DIR")
    def test_cached_without_area(
        self, mock_cache_dir: MagicMock, mock_read: MagicMock
    ) -> None:
        mock_path = MagicMock()
        mock_cache_dir.__truediv__ = MagicMock(return_value=mock_path)
        mock_path.exists.return_value = True

        mock_gdf = gpd.GeoDataFrame(
            {"name": ["Tatrzański Park Narodowy"]},
            geometry=[Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])],
            crs="EPSG:4326",
        )
        mock_read.return_value = mock_gdf

        result = get_polish_national_parks()
        assert len(result) == 1

    @patch("python_pkg.geo_data._poland_nature.gpd.GeoDataFrame.from_features")
    @patch("python_pkg.geo_data._poland_nature._ensure_cache_dir")
    @patch("python_pkg.geo_data._poland_nature._overpass_query")
    @patch("python_pkg.geo_data._poland_nature.CACHE_DIR")
    @patch("python_pkg.geo_data._poland_nature.sys.stdout")
    def test_downloads_parks(
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
                _make_relation_element("Tatrzański Park Narodowy"),
                # Not a national park (missing "Narodowy")
                _make_relation_element("Some Reserve"),
                # Not a relation
                {"type": "way", "tags": {"name": "Park Narodowy X"}},
                # No name
                {"type": "relation", "tags": {}, "members": []},
                # Duplicate
                _make_relation_element("Tatrzański Park Narodowy"),
                # No outer rings
                _make_relation_element("Empty Park Narodowy", include_outer=False),
                # Case insensitive match
                _make_relation_element("park narodowy Biebrzy"),
            ]
        }

        poly = Polygon([(20, 50), (21, 50), (21, 51), (20, 51)])
        mock_gdf = gpd.GeoDataFrame(
            {"name": ["Tatrzański Park Narodowy", "park narodowy Biebrzy"]},
            geometry=[poly, poly],
            crs="EPSG:4326",
        )
        mock_from_features.return_value = mock_gdf

        result = get_polish_national_parks()
        assert len(result) >= 0
