"""Tests for metro stations and osiedla download paths."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import geopandas as gpd

from python_pkg.geo_data._warsaw import (
    get_warsaw_metro_stations,
    get_warsaw_osiedla,
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


class TestGetWarsawMetroStations:
    """Tests for get_warsaw_metro_stations."""

    @patch("python_pkg.geo_data._warsaw.gpd.read_file")
    @patch("python_pkg.geo_data._warsaw.CACHE_DIR")
    def test_cached(self, mock_cache_dir: MagicMock, mock_read: MagicMock) -> None:
        mock_path = MagicMock()
        mock_cache_dir.__truediv__ = MagicMock(return_value=mock_path)
        mock_path.exists.return_value = True
        mock_gdf = MagicMock(spec=gpd.GeoDataFrame)
        mock_read.return_value = mock_gdf
        result = get_warsaw_metro_stations()
        assert result is mock_gdf

    @patch("python_pkg.geo_data._warsaw.gpd.GeoDataFrame.from_features")
    @patch("python_pkg.geo_data._warsaw._ensure_cache_dir")
    @patch("python_pkg.geo_data._warsaw._overpass_query")
    @patch("python_pkg.geo_data._warsaw.CACHE_DIR")
    @patch("python_pkg.geo_data._warsaw.sys.stdout")
    def test_downloads_metro(
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
                # M1 only station
                {
                    "type": "node",
                    "tags": {"name": "Kabaty"},
                    "lon": 21.0,
                    "lat": 52.1,
                },
                # M2 only station
                {
                    "type": "node",
                    "tags": {"name": "Bródno"},
                    "lon": 21.0,
                    "lat": 52.3,
                },
                # M1/M2 interchange
                {
                    "type": "node",
                    "tags": {"name": "Świętokrzyska"},
                    "lon": 21.0,
                    "lat": 52.2,
                },
                # Unknown station
                {
                    "type": "node",
                    "tags": {"name": "Nowa Stacja"},
                    "lon": 21.0,
                    "lat": 52.4,
                },
                # Not a node -> skip
                {
                    "type": "way",
                    "tags": {"name": "Metro Line"},
                },
                # Node without name -> skip
                {
                    "type": "node",
                    "tags": {},
                    "lon": 21.0,
                    "lat": 52.0,
                },
                # Duplicate
                {
                    "type": "node",
                    "tags": {"name": "Kabaty"},
                    "lon": 21.0,
                    "lat": 52.1,
                },
            ]
        }

        mock_gdf = MagicMock(spec=gpd.GeoDataFrame)
        mock_from_features.return_value = mock_gdf

        result = get_warsaw_metro_stations()
        assert result is mock_gdf


class TestGetWarsawOsiedla:
    """Tests for get_warsaw_osiedla."""

    @patch("python_pkg.geo_data._warsaw.gpd.read_file")
    @patch("python_pkg.geo_data._warsaw.CACHE_DIR")
    def test_cached(self, mock_cache_dir: MagicMock, mock_read: MagicMock) -> None:
        mock_path = MagicMock()
        mock_cache_dir.__truediv__ = MagicMock(return_value=mock_path)
        mock_path.exists.return_value = True
        mock_gdf = MagicMock(spec=gpd.GeoDataFrame)
        mock_read.return_value = mock_gdf
        result = get_warsaw_osiedla()
        assert result is mock_gdf

    @patch("python_pkg.geo_data._warsaw.gpd.GeoDataFrame.from_features")
    @patch("python_pkg.geo_data._warsaw._ensure_cache_dir")
    @patch("python_pkg.geo_data._warsaw._overpass_query")
    @patch("python_pkg.geo_data._warsaw.CACHE_DIR")
    @patch("python_pkg.geo_data._warsaw.sys.stdout")
    def test_downloads_osiedla(
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
                _make_relation_element("Mokotów"),
                # Not a relation -> skip
                {
                    "type": "way",
                    "tags": {"name": "Way Osiedle"},
                },
                # No name
                {"type": "relation", "tags": {}, "members": []},
                # Duplicate
                _make_relation_element("Mokotów"),
                # No outer rings
                _make_relation_element("Empty", include_outer=False),
            ]
        }

        mock_gdf = MagicMock(spec=gpd.GeoDataFrame)
        mock_from_features.return_value = mock_gdf

        result = get_warsaw_osiedla()
        assert result is mock_gdf
