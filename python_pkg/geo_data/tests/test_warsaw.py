"""Tests for python_pkg.geo_data._warsaw module."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import geopandas as gpd
from shapely.geometry import LineString, Polygon

from python_pkg.geo_data._warsaw import (
    _merge_bridge_segments,
    get_vistula_river,
    get_warsaw_boundary,
    get_warsaw_bridges,
    get_warsaw_districts,
)


class TestGetWarsawBoundary:
    """Tests for get_warsaw_boundary."""

    @patch("python_pkg.geo_data._warsaw.gpd.read_file")
    @patch("python_pkg.geo_data._warsaw.CACHE_DIR")
    def test_cached(self, mock_cache_dir: MagicMock, mock_read: MagicMock) -> None:
        mock_path = MagicMock()
        mock_cache_dir.__truediv__ = MagicMock(return_value=mock_path)
        mock_path.exists.return_value = True

        mock_gdf = MagicMock(spec=gpd.GeoDataFrame)
        mock_read.return_value = mock_gdf

        result = get_warsaw_boundary()
        assert result is mock_gdf

    @patch("python_pkg.geo_data._warsaw.gpd.GeoDataFrame.to_file")
    @patch("python_pkg.geo_data._warsaw._ensure_cache_dir")
    @patch("python_pkg.geo_data._warsaw.gpd.read_file")
    @patch("python_pkg.geo_data._warsaw._PKG_DIR")
    @patch("python_pkg.geo_data._warsaw.CACHE_DIR")
    def test_from_districts_file_with_warszawa(
        self,
        mock_cache_dir: MagicMock,
        mock_pkg_dir: MagicMock,
        mock_read: MagicMock,
        mock_ensure: MagicMock,
        mock_to_file: MagicMock,
    ) -> None:
        mock_cache_path = MagicMock()
        mock_cache_dir.__truediv__ = MagicMock(return_value=mock_cache_path)
        mock_cache_path.exists.return_value = False

        mock_districts_path = MagicMock()
        mock_pkg_dir.__truediv__ = MagicMock(return_value=MagicMock())
        mock_pkg_dir.__truediv__.return_value.__truediv__ = MagicMock(
            return_value=MagicMock()
        )
        mock_pkg_dir.__truediv__.return_value.__truediv__.return_value.__truediv__ = (
            MagicMock(return_value=mock_districts_path)
        )
        mock_districts_path.exists.return_value = True

        mock_warsaw_gdf = gpd.GeoDataFrame(
            {"name": ["Warszawa", "Mokotów"]},
            geometry=[
                Polygon([(20, 52), (21, 52), (21, 53), (20, 53)]),
                Polygon([(20.5, 52.5), (20.6, 52.5), (20.6, 52.6), (20.5, 52.6)]),
            ],
            crs="EPSG:4326",
        )
        mock_read.return_value = mock_warsaw_gdf

        result = get_warsaw_boundary()
        assert len(result) == 1

    @patch("python_pkg.geo_data._warsaw.gpd.GeoDataFrame.to_file")
    @patch("python_pkg.geo_data._warsaw._ensure_cache_dir")
    @patch("python_pkg.geo_data._warsaw.gpd.read_file")
    @patch("python_pkg.geo_data._warsaw._PKG_DIR")
    @patch("python_pkg.geo_data._warsaw.CACHE_DIR")
    def test_from_districts_file_no_warszawa_entry(
        self,
        mock_cache_dir: MagicMock,
        mock_pkg_dir: MagicMock,
        mock_read: MagicMock,
        mock_ensure: MagicMock,
        mock_to_file: MagicMock,
    ) -> None:
        mock_cache_path = MagicMock()
        mock_cache_dir.__truediv__ = MagicMock(return_value=mock_cache_path)
        mock_cache_path.exists.return_value = False

        mock_districts_path = MagicMock()
        mock_pkg_dir.__truediv__ = MagicMock(return_value=MagicMock())
        mock_pkg_dir.__truediv__.return_value.__truediv__ = MagicMock(
            return_value=MagicMock()
        )
        mock_pkg_dir.__truediv__.return_value.__truediv__.return_value.__truediv__ = (
            MagicMock(return_value=mock_districts_path)
        )
        mock_districts_path.exists.return_value = True

        # No "Warszawa" entry
        mock_warsaw_gdf = gpd.GeoDataFrame(
            {"name": ["Mokotów", "Śródmieście"]},
            geometry=[
                Polygon([(20, 52), (21, 52), (21, 53), (20, 53)]),
                Polygon([(20.5, 52.5), (20.6, 52.5), (20.6, 52.6), (20.5, 52.6)]),
            ],
            crs="EPSG:4326",
        )
        mock_read.return_value = mock_warsaw_gdf

        result = get_warsaw_boundary()
        assert len(result) == 1

    @patch("python_pkg.geo_data._warsaw.gpd.GeoDataFrame.from_features")
    @patch("python_pkg.geo_data._warsaw._ensure_cache_dir")
    @patch("python_pkg.geo_data._warsaw._overpass_query")
    @patch("python_pkg.geo_data._warsaw._PKG_DIR")
    @patch("python_pkg.geo_data._warsaw.CACHE_DIR")
    @patch("python_pkg.geo_data._warsaw.sys.stdout")
    def test_fallback_overpass(
        self,
        mock_stdout: MagicMock,
        mock_cache_dir: MagicMock,
        mock_pkg_dir: MagicMock,
        mock_query: MagicMock,
        mock_ensure: MagicMock,
        mock_from_features: MagicMock,
    ) -> None:
        mock_cache_path = MagicMock()
        mock_cache_dir.__truediv__ = MagicMock(return_value=mock_cache_path)
        mock_cache_path.exists.return_value = False

        mock_districts_path = MagicMock()
        mock_pkg_dir.__truediv__ = MagicMock(return_value=MagicMock())
        mock_pkg_dir.__truediv__.return_value.__truediv__ = MagicMock(
            return_value=MagicMock()
        )
        mock_pkg_dir.__truediv__.return_value.__truediv__.return_value.__truediv__ = (
            MagicMock(return_value=mock_districts_path)
        )
        mock_districts_path.exists.return_value = False

        mock_query.return_value = {
            "elements": [
                {
                    "type": "relation",
                    "members": [
                        {
                            "role": "outer",
                            "geometry": [
                                {"lon": 20, "lat": 52},
                                {"lon": 21, "lat": 52},
                                {"lon": 21, "lat": 53},
                            ],
                        },
                        # non-outer member
                        {
                            "role": "inner",
                            "geometry": [
                                {"lon": 20.5, "lat": 52.5},
                            ],
                        },
                    ],
                },
                # Not a relation
                {"type": "way"},
                # Relation with no outer geometry (empty coords)
                {
                    "type": "relation",
                    "members": [
                        {"role": "inner", "geometry": [{"lon": 20, "lat": 52}]},
                    ],
                },
            ]
        }

        mock_gdf = MagicMock(spec=gpd.GeoDataFrame)
        mock_from_features.return_value = mock_gdf

        result = get_warsaw_boundary()
        assert result is mock_gdf


class TestGetWarsawDistricts:
    """Tests for get_warsaw_districts."""

    @patch("python_pkg.geo_data._warsaw.gpd.read_file")
    @patch("python_pkg.geo_data._warsaw._PKG_DIR")
    def test_districts_file_exists(
        self, mock_pkg_dir: MagicMock, mock_read: MagicMock
    ) -> None:
        mock_districts_path = MagicMock()
        mock_pkg_dir.__truediv__ = MagicMock(return_value=MagicMock())
        mock_pkg_dir.__truediv__.return_value.__truediv__ = MagicMock(
            return_value=MagicMock()
        )
        mock_pkg_dir.__truediv__.return_value.__truediv__.return_value.__truediv__ = (
            MagicMock(return_value=mock_districts_path)
        )
        mock_districts_path.exists.return_value = True

        mock_gdf = gpd.GeoDataFrame(
            {"name": ["Warszawa", "Mokotów", "Śródmieście"]},
            geometry=[
                Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
                Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
                Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
            ],
            crs="EPSG:4326",
        )
        mock_read.return_value = mock_gdf

        result = get_warsaw_districts()
        assert "Warszawa" not in result["name"].values

    @patch("python_pkg.geo_data._warsaw._PKG_DIR")
    def test_districts_file_not_found(self, mock_pkg_dir: MagicMock) -> None:
        mock_districts_path = MagicMock()
        mock_pkg_dir.__truediv__ = MagicMock(return_value=MagicMock())
        mock_pkg_dir.__truediv__.return_value.__truediv__ = MagicMock(
            return_value=MagicMock()
        )
        mock_pkg_dir.__truediv__.return_value.__truediv__.return_value.__truediv__ = (
            MagicMock(return_value=mock_districts_path)
        )
        mock_districts_path.exists.return_value = False

        import pytest

        with pytest.raises(FileNotFoundError, match="Warsaw districts GeoJSON"):
            get_warsaw_districts()


class TestGetVistulaRiver:
    """Tests for get_vistula_river."""

    @patch("python_pkg.geo_data._warsaw.gpd.read_file")
    @patch("python_pkg.geo_data._warsaw.CACHE_DIR")
    def test_cached(self, mock_cache_dir: MagicMock, mock_read: MagicMock) -> None:
        mock_path = MagicMock()
        mock_cache_dir.__truediv__ = MagicMock(return_value=mock_path)
        mock_path.exists.return_value = True

        mock_gdf = MagicMock(spec=gpd.GeoDataFrame)
        mock_read.return_value = mock_gdf

        result = get_vistula_river()
        assert result is mock_gdf

    @patch("python_pkg.geo_data._warsaw.gpd.GeoDataFrame.from_features")
    @patch("python_pkg.geo_data._warsaw._ensure_cache_dir")
    @patch("python_pkg.geo_data._warsaw._overpass_query")
    @patch("python_pkg.geo_data._warsaw.CACHE_DIR")
    @patch("python_pkg.geo_data._warsaw.sys.stdout")
    def test_downloads(
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
                    "type": "way",
                    "geometry": [
                        {"lon": 20.0, "lat": 52.0},
                        {"lon": 21.0, "lat": 52.5},
                    ],
                },
                # Too few coords
                {
                    "type": "way",
                    "geometry": [{"lon": 20.0, "lat": 52.0}],
                },
                # Not a way
                {"type": "node"},
                # Way without geometry
                {"type": "way"},
            ]
        }

        mock_gdf = MagicMock(spec=gpd.GeoDataFrame)
        mock_from_features.return_value = mock_gdf

        result = get_vistula_river()
        assert result is mock_gdf


class TestGetWarsawBridges:
    """Tests for get_warsaw_bridges."""

    @patch("python_pkg.geo_data._warsaw.gpd.read_file")
    @patch("python_pkg.geo_data._warsaw.CACHE_DIR")
    def test_cached(self, mock_cache_dir: MagicMock, mock_read: MagicMock) -> None:
        mock_path = MagicMock()
        mock_cache_dir.__truediv__ = MagicMock(return_value=mock_path)
        mock_path.exists.return_value = True

        mock_gdf = MagicMock(spec=gpd.GeoDataFrame)
        mock_read.return_value = mock_gdf

        result = get_warsaw_bridges()
        assert result is mock_gdf

    @patch("python_pkg.geo_data._warsaw.gpd.GeoDataFrame.from_features")
    @patch("python_pkg.geo_data._warsaw._ensure_cache_dir")
    @patch("python_pkg.geo_data._warsaw._overpass_query")
    @patch("python_pkg.geo_data._warsaw.get_vistula_river")
    @patch("python_pkg.geo_data._warsaw.CACHE_DIR")
    @patch("python_pkg.geo_data._warsaw.sys.stdout")
    def test_downloads(
        self,
        mock_stdout: MagicMock,
        mock_cache_dir: MagicMock,
        mock_vistula: MagicMock,
        mock_query: MagicMock,
        mock_ensure: MagicMock,
        mock_from_features: MagicMock,
    ) -> None:
        mock_path = MagicMock()
        mock_cache_dir.__truediv__ = MagicMock(return_value=mock_path)
        mock_path.exists.return_value = False

        # Create a real Vistula geometry for intersection tests
        vistula_gdf = gpd.GeoDataFrame(
            {"name": ["Wisła"]},
            geometry=[LineString([(20.0, 52.2), (21.0, 52.2)])],
            crs="EPSG:4326",
        )
        mock_vistula.return_value = vistula_gdf

        mock_query.return_value = {
            "elements": [
                # Bridge that intersects vistula buffer
                {
                    "type": "way",
                    "id": 1,
                    "tags": {"name": "Most Łazienkowski"},
                    "geometry": [
                        {"lon": 20.5, "lat": 52.19},
                        {"lon": 20.5, "lat": 52.21},
                    ],
                },
                # Bridge far from vistula
                {
                    "type": "way",
                    "id": 2,
                    "tags": {"name": "Most Daleki"},
                    "geometry": [
                        {"lon": 20.5, "lat": 55.0},
                        {"lon": 20.5, "lat": 55.1},
                    ],
                },
                # Not a way
                {"type": "node", "tags": {"name": "Most X"}},
                # Way without geometry
                {"type": "way", "tags": {"name": "Most Y"}},
                # No name
                {
                    "type": "way",
                    "id": 3,
                    "tags": {},
                    "geometry": [
                        {"lon": 20.5, "lat": 52.19},
                        {"lon": 20.5, "lat": 52.21},
                    ],
                },
                # Duplicate
                {
                    "type": "way",
                    "id": 4,
                    "tags": {"name": "Most Łazienkowski"},
                    "geometry": [
                        {"lon": 20.5, "lat": 52.19},
                        {"lon": 20.5, "lat": 52.21},
                    ],
                },
                # Too few coords
                {
                    "type": "way",
                    "id": 5,
                    "tags": {"name": "Most Short"},
                    "geometry": [{"lon": 20.5, "lat": 52.19}],
                },
            ]
        }

        mock_gdf = MagicMock(spec=gpd.GeoDataFrame)
        mock_from_features.return_value = mock_gdf

        result = get_warsaw_bridges()
        assert result is mock_gdf


class TestMergeBridgeSegments:
    """Tests for _merge_bridge_segments."""

    def test_single_segment(self) -> None:
        features: list[dict[str, Any]] = [
            {
                "properties": {"name": "Most A"},
                "geometry": {"coordinates": [(20, 52), (21, 52)]},
            }
        ]
        result = _merge_bridge_segments(features)
        assert len(result) == 1
        assert result[0]["geometry"]["type"] == "LineString"

    def test_multiple_segments_same_name(self) -> None:
        features: list[dict[str, Any]] = [
            {
                "properties": {"name": "Most A"},
                "geometry": {"coordinates": [(20, 52), (21, 52)]},
            },
            {
                "properties": {"name": "Most A"},
                "geometry": {"coordinates": [(21, 52), (22, 52)]},
            },
        ]
        result = _merge_bridge_segments(features)
        assert len(result) == 1
        assert result[0]["geometry"]["type"] == "MultiLineString"
