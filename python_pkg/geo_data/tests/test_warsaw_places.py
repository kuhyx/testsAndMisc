"""Tests for python_pkg.geo_data._warsaw_places module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import geopandas as gpd
from shapely.geometry import LineString

from python_pkg.geo_data._warsaw_places import (
    _filter_streets_by_length,
    get_warsaw_landmarks,
    get_warsaw_streets,
)


class TestGetWarsawStreets:
    """Tests for get_warsaw_streets."""

    @patch("python_pkg.geo_data._warsaw_places._filter_streets_by_length")
    @patch("python_pkg.geo_data._warsaw_places.gpd.read_file")
    @patch("python_pkg.geo_data._warsaw_places.CACHE_DIR")
    def test_cached(
        self,
        mock_cache_dir: MagicMock,
        mock_read: MagicMock,
        mock_filter: MagicMock,
    ) -> None:
        mock_path = MagicMock()
        mock_cache_dir.__truediv__ = MagicMock(return_value=mock_path)
        mock_path.exists.return_value = True

        mock_gdf = MagicMock(spec=gpd.GeoDataFrame)
        mock_read.return_value = mock_gdf
        mock_filter.return_value = mock_gdf

        result = get_warsaw_streets()
        assert result is mock_gdf

    @patch("python_pkg.geo_data._warsaw_places._filter_streets_by_length")
    @patch("python_pkg.geo_data._warsaw_places.gpd.GeoDataFrame.from_features")
    @patch("python_pkg.geo_data._warsaw_places._ensure_cache_dir")
    @patch("python_pkg.geo_data._warsaw_places._overpass_query")
    @patch("python_pkg.geo_data._warsaw_places.CACHE_DIR")
    @patch("python_pkg.geo_data._warsaw_places.sys.stdout")
    def test_downloads(
        self,
        mock_stdout: MagicMock,
        mock_cache_dir: MagicMock,
        mock_query: MagicMock,
        mock_ensure: MagicMock,
        mock_from_features: MagicMock,
        mock_filter: MagicMock,
    ) -> None:
        mock_path = MagicMock()
        mock_cache_dir.__truediv__ = MagicMock(return_value=mock_path)
        mock_path.exists.return_value = False

        mock_query.return_value = {
            "elements": [
                {
                    "type": "way",
                    "tags": {"name": "Marszałkowska", "highway": "primary"},
                    "geometry": [
                        {"lon": 21.0, "lat": 52.2},
                        {"lon": 21.0, "lat": 52.3},
                    ],
                },
                # Too few coords
                {
                    "type": "way",
                    "tags": {"name": "Short"},
                    "geometry": [{"lon": 21.0, "lat": 52.2}],
                },
                # Not a way
                {"type": "node", "tags": {"name": "Node"}},
                # Way without geometry
                {"type": "way", "tags": {"name": "NoGeom"}},
            ]
        }

        mock_gdf = MagicMock(spec=gpd.GeoDataFrame)
        mock_from_features.return_value = mock_gdf
        mock_filter.return_value = mock_gdf

        result = get_warsaw_streets()
        assert result is mock_gdf


class TestFilterStreetsByLength:
    """Tests for _filter_streets_by_length."""

    def test_filters_and_merges(self) -> None:
        gdf = gpd.GeoDataFrame(
            {
                "name": ["Marszałkowska", "Marszałkowska", "Unknown", "Short"],
                "geometry": [
                    LineString([(21.0, 52.2), (21.0, 52.3)]),
                    LineString([(21.0, 52.3), (21.0, 52.4)]),
                    LineString([(21.0, 52.2), (21.0, 52.3)]),
                    LineString([(21.0, 52.2), (21.001, 52.2001)]),
                ],
            },
            crs="EPSG:4326",
        )
        result = _filter_streets_by_length(gdf, 500)
        # Only streets >= 500m should be included
        for _, row in result.iterrows():
            assert row["length_m"] >= 500

    def test_single_segment(self) -> None:
        gdf = gpd.GeoDataFrame(
            {
                "name": ["Marszałkowska"],
                "geometry": [LineString([(21.0, 52.2), (21.0, 52.3)])],
            },
            crs="EPSG:4326",
        )
        result = _filter_streets_by_length(gdf, 0)
        # Single segment should remain a LineString
        assert len(result) == 1

    def test_unknown_name_excluded(self) -> None:
        gdf = gpd.GeoDataFrame(
            {
                "name": ["Unknown"],
                "geometry": [LineString([(21.0, 52.2), (21.0, 52.3)])],
            },
            crs="EPSG:4326",
        )
        result = _filter_streets_by_length(gdf, 0)
        assert len(result) == 0

    def test_empty_name_excluded(self) -> None:
        gdf = gpd.GeoDataFrame(
            {
                "name": [""],
                "geometry": [LineString([(21.0, 52.2), (21.0, 52.3)])],
            },
            crs="EPSG:4326",
        )
        result = _filter_streets_by_length(gdf, 0)
        assert len(result) == 0

    def test_no_name_column(self) -> None:
        gdf = gpd.GeoDataFrame(
            {
                "geometry": [LineString([(21.0, 52.2), (21.0, 52.3)])],
            },
            crs="EPSG:4326",
        )
        result = _filter_streets_by_length(gdf, 0)
        assert len(result) == 0


class TestGetWarsawLandmarks:
    """Tests for get_warsaw_landmarks."""

    @patch("python_pkg.geo_data._warsaw_places.gpd.read_file")
    @patch("python_pkg.geo_data._warsaw_places.CACHE_DIR")
    def test_cached(self, mock_cache_dir: MagicMock, mock_read: MagicMock) -> None:
        mock_path = MagicMock()
        mock_cache_dir.__truediv__ = MagicMock(return_value=mock_path)
        mock_path.exists.return_value = True

        mock_gdf = MagicMock(spec=gpd.GeoDataFrame)
        mock_read.return_value = mock_gdf

        result = get_warsaw_landmarks()
        assert result is mock_gdf

    @patch("python_pkg.geo_data._warsaw_places.gpd.GeoDataFrame.from_features")
    @patch("python_pkg.geo_data._warsaw_places._ensure_cache_dir")
    @patch("python_pkg.geo_data._warsaw_places._overpass_query")
    @patch("python_pkg.geo_data._warsaw_places.CACHE_DIR")
    @patch("python_pkg.geo_data._warsaw_places.sys.stdout")
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
                # Node with tourism
                {
                    "type": "node",
                    "tags": {"name": "Muzeum Chopina", "tourism": "museum"},
                    "lon": 21.0,
                    "lat": 52.2,
                },
                # Way with center
                {
                    "type": "way",
                    "tags": {"name": "Łazienki", "tourism": "attraction"},
                    "center": {"lon": 21.0, "lat": 52.2},
                },
                # Node with historic
                {
                    "type": "node",
                    "tags": {"name": "Kolumna Zygmunta", "historic": "monument"},
                    "lon": 21.0,
                    "lat": 52.2,
                },
                # Node with leisure
                {
                    "type": "node",
                    "tags": {"name": "Park Skaryszewski", "leisure": "park"},
                    "lon": 21.0,
                    "lat": 52.2,
                },
                # Node no tourism/historic/leisure -> "landmark"
                {
                    "type": "node",
                    "tags": {"name": "Generic"},
                    "lon": 21.0,
                    "lat": 52.2,
                },
                # Duplicate
                {
                    "type": "node",
                    "tags": {"name": "Muzeum Chopina", "tourism": "museum"},
                    "lon": 21.0,
                    "lat": 52.2,
                },
                # No name
                {
                    "type": "node",
                    "tags": {"tourism": "museum"},
                    "lon": 21.0,
                    "lat": 52.2,
                },
                # Way without center
                {
                    "type": "way",
                    "tags": {"name": "No Center"},
                },
            ]
        }

        mock_gdf = MagicMock(spec=gpd.GeoDataFrame)
        mock_from_features.return_value = mock_gdf

        result = get_warsaw_landmarks()
        assert result is mock_gdf

    @patch("python_pkg.geo_data._warsaw_places._ensure_cache_dir")
    @patch("python_pkg.geo_data._warsaw_places._overpass_query")
    @patch("python_pkg.geo_data._warsaw_places.CACHE_DIR")
    @patch("python_pkg.geo_data._warsaw_places.sys.stdout")
    def test_empty_result(
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

        result = get_warsaw_landmarks()
        assert len(result) == 0
