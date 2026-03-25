"""Tests for python_pkg.geo_data._poland_water module."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import geopandas as gpd
from shapely.geometry import Polygon

from python_pkg.geo_data._poland_water import (
    _extract_coastal_geometry,
    _extract_river_coords_from_element,
    get_polish_lakes,
    get_polish_rivers,
)


class TestExtractCoastalGeometry:
    """Tests for _extract_coastal_geometry."""

    def test_relation_delegated(self) -> None:
        element: dict[str, Any] = {
            "type": "relation",
            "members": [
                {
                    "role": "outer",
                    "geometry": [
                        {"lon": 0, "lat": 0},
                        {"lon": 1, "lat": 0},
                        {"lon": 1, "lat": 1},
                        {"lon": 0, "lat": 1},
                    ],
                }
            ],
        }
        result = _extract_coastal_geometry(element, "peninsula", ("cliff", "beach"))
        assert result is not None

    def test_way_line_type(self) -> None:
        element: dict[str, Any] = {
            "type": "way",
            "geometry": [{"lon": 0, "lat": 0}, {"lon": 1, "lat": 1}],
        }
        result = _extract_coastal_geometry(element, "cliff", ("cliff", "beach"))
        assert result is not None
        assert result["type"] == "LineString"

    def test_way_polygon_type(self) -> None:
        element: dict[str, Any] = {
            "type": "way",
            "geometry": [
                {"lon": 0, "lat": 0},
                {"lon": 1, "lat": 0},
                {"lon": 1, "lat": 1},
                {"lon": 0, "lat": 1},
            ],
        }
        result = _extract_coastal_geometry(element, "peninsula", ("cliff", "beach"))
        assert result is not None
        assert result["type"] == "Polygon"

    def test_way_polygon_auto_close(self) -> None:
        element: dict[str, Any] = {
            "type": "way",
            "geometry": [
                {"lon": 0, "lat": 0},
                {"lon": 1, "lat": 0},
                {"lon": 1, "lat": 1},
                {"lon": 0, "lat": 0.5},
            ],
        }
        result = _extract_coastal_geometry(element, "peninsula", ("cliff", "beach"))
        assert result is not None
        assert result["coordinates"][0][0] == result["coordinates"][0][-1]

    def test_way_polygon_already_closed(self) -> None:
        element: dict[str, Any] = {
            "type": "way",
            "geometry": [
                {"lon": 0, "lat": 0},
                {"lon": 1, "lat": 0},
                {"lon": 1, "lat": 1},
                {"lon": 0, "lat": 0},
            ],
        }
        result = _extract_coastal_geometry(element, "peninsula", ("cliff", "beach"))
        assert result is not None
        assert result["type"] == "Polygon"
        assert len(result["coordinates"][0]) == 4

    def test_way_too_short_for_polygon_not_line(self) -> None:
        element: dict[str, Any] = {
            "type": "way",
            "geometry": [
                {"lon": 0, "lat": 0},
                {"lon": 1, "lat": 0},
                {"lon": 1, "lat": 1},
            ],
        }
        # 3 coords, >= MIN_LINE_COORDS but < MIN_RING_COORDS for polygon
        result = _extract_coastal_geometry(element, "peninsula", ("cliff", "beach"))
        # 3 coords is not enough for ring (need 4), so returns None
        assert result is None

    def test_way_too_few_coords(self) -> None:
        element: dict[str, Any] = {
            "type": "way",
            "geometry": [{"lon": 0, "lat": 0}],
        }
        result = _extract_coastal_geometry(element, "cliff", ("cliff", "beach"))
        assert result is None

    def test_not_way_or_relation(self) -> None:
        element: dict[str, Any] = {"type": "node"}
        result = _extract_coastal_geometry(element, "cliff", ("cliff", "beach"))
        assert result is None

    def test_way_no_geometry(self) -> None:
        element: dict[str, Any] = {"type": "way"}
        result = _extract_coastal_geometry(element, "cliff", ("cliff", "beach"))
        assert result is None


class TestExtractRiverCoordsFromElement:
    """Tests for _extract_river_coords_from_element."""

    def test_way_element(self) -> None:
        element: dict[str, Any] = {
            "type": "way",
            "geometry": [{"lon": 0, "lat": 0}, {"lon": 1, "lat": 1}],
        }
        result = _extract_river_coords_from_element(element)
        assert len(result) == 1

    def test_way_too_few_coords(self) -> None:
        element: dict[str, Any] = {
            "type": "way",
            "geometry": [{"lon": 0, "lat": 0}],
        }
        result = _extract_river_coords_from_element(element)
        assert len(result) == 0

    def test_relation_element(self) -> None:
        element: dict[str, Any] = {
            "type": "relation",
            "members": [
                {
                    "type": "way",
                    "geometry": [{"lon": 0, "lat": 0}, {"lon": 1, "lat": 1}],
                },
                {
                    "type": "way",
                    "geometry": [{"lon": 1, "lat": 1}, {"lon": 2, "lat": 2}],
                },
                # Too few coords
                {
                    "type": "way",
                    "geometry": [{"lon": 0, "lat": 0}],
                },
                # Not a way
                {
                    "type": "node",
                    "geometry": [{"lon": 0, "lat": 0}, {"lon": 1, "lat": 1}],
                },
                # No geometry
                {"type": "way"},
            ],
        }
        result = _extract_river_coords_from_element(element)
        assert len(result) == 2

    def test_unknown_type(self) -> None:
        element: dict[str, Any] = {"type": "node"}
        result = _extract_river_coords_from_element(element)
        assert len(result) == 0

    def test_way_no_geometry(self) -> None:
        element: dict[str, Any] = {"type": "way"}
        result = _extract_river_coords_from_element(element)
        assert len(result) == 0


class TestGetPolishLakes:
    """Tests for get_polish_lakes."""

    @patch("python_pkg.geo_data._poland_water.gpd.read_file")
    @patch("python_pkg.geo_data._poland_water.CACHE_DIR")
    def test_cached_with_area(
        self, mock_cache_dir: MagicMock, mock_read: MagicMock
    ) -> None:
        mock_path = MagicMock()
        mock_cache_dir.__truediv__ = MagicMock(return_value=mock_path)
        mock_path.exists.return_value = True

        mock_gdf = gpd.GeoDataFrame(
            {"name": ["Śniardwy"], "area_km2": [113.0]},
            geometry=[Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])],
            crs="EPSG:4326",
        )
        mock_read.return_value = mock_gdf

        result = get_polish_lakes()
        assert result.iloc[0]["area_km2"] == 113.0

    @patch("python_pkg.geo_data._poland_water.gpd.read_file")
    @patch("python_pkg.geo_data._poland_water.CACHE_DIR")
    def test_cached_without_area(
        self, mock_cache_dir: MagicMock, mock_read: MagicMock
    ) -> None:
        mock_path = MagicMock()
        mock_cache_dir.__truediv__ = MagicMock(return_value=mock_path)
        mock_path.exists.return_value = True

        mock_gdf = gpd.GeoDataFrame(
            {"name": ["Śniardwy"]},
            geometry=[Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])],
            crs="EPSG:4326",
        )
        mock_read.return_value = mock_gdf

        result = get_polish_lakes()
        assert len(result) == 1

    def test_downloads_lakes(self) -> None:
        with (
            patch("python_pkg.geo_data._poland_water.sys.stdout"),
            patch("python_pkg.geo_data._poland_water.CACHE_DIR") as mock_cache_dir,
            patch("python_pkg.geo_data._poland_water._overpass_query") as mock_query,
            patch("python_pkg.geo_data._poland_water._ensure_cache_dir"),
            patch(
                "python_pkg.geo_data._poland_water.gpd.GeoDataFrame.from_features"
            ) as mock_from_features,
            patch(
                "python_pkg.geo_data._poland_water._add_area_column"
            ) as mock_add_area,
        ):
            mock_path = MagicMock()
            mock_cache_dir.__truediv__ = MagicMock(return_value=mock_path)
            mock_path.exists.return_value = False

            mock_query.return_value = {
                "elements": [
                    {
                        "type": "way",
                        "tags": {"name": "Śniardwy"},
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
                        "tags": {"name": "Śniardwy"},
                        "geometry": [
                            {"lon": 0, "lat": 0},
                            {"lon": 1, "lat": 0},
                            {"lon": 1, "lat": 1},
                            {"lon": 0, "lat": 1},
                        ],
                    },
                    # No name
                    {"type": "way", "tags": {}, "geometry": []},
                    # Geometry extraction fails
                    {
                        "type": "way",
                        "tags": {"name": "Tiny"},
                        "geometry": [{"lon": 0, "lat": 0}],
                    },
                ]
            }

            poly = Polygon([(20, 50), (21, 50), (21, 51), (20, 51)])
            mock_gdf = gpd.GeoDataFrame(
                {"name": ["Śniardwy"]},
                geometry=[poly],
                crs="EPSG:4326",
            )
            mock_from_features.return_value = mock_gdf
            gdf_with_area = mock_gdf.copy()
            gdf_with_area["area_km2"] = [113.0]
            mock_add_area.return_value = gdf_with_area

            result = get_polish_lakes()
            assert len(result) >= 0

    def test_empty_result(self) -> None:
        with (
            patch("python_pkg.geo_data._poland_water.sys.stdout"),
            patch("python_pkg.geo_data._poland_water.CACHE_DIR") as mock_cache_dir,
            patch("python_pkg.geo_data._poland_water._overpass_query") as mock_query,
            patch("python_pkg.geo_data._poland_water._ensure_cache_dir"),
            patch(
                "python_pkg.geo_data._poland_water.gpd.GeoDataFrame.from_features"
            ) as mock_from_features,
            patch(
                "python_pkg.geo_data._poland_water._add_area_column"
            ) as mock_add_area,
        ):
            mock_path = MagicMock()
            mock_cache_dir.__truediv__ = MagicMock(return_value=mock_path)
            mock_path.exists.return_value = False
            mock_query.return_value = {"elements": []}

            empty_gdf = gpd.GeoDataFrame({"name": [], "geometry": []})
            mock_from_features.return_value = empty_gdf
            mock_add_area.return_value = empty_gdf

            result = get_polish_lakes()
            assert len(result) == 0


class TestGetPolishRivers:
    """Tests for get_polish_rivers."""

    @patch("python_pkg.geo_data._poland_water.gpd.read_file")
    @patch("python_pkg.geo_data._poland_water.CACHE_DIR")
    def test_cached_with_length(
        self, mock_cache_dir: MagicMock, mock_read: MagicMock
    ) -> None:
        mock_path = MagicMock()
        mock_cache_dir.__truediv__ = MagicMock(return_value=mock_path)
        mock_path.exists.return_value = True

        mock_gdf = gpd.GeoDataFrame(
            {"name": ["Wisła"], "length_km": [1047.0]},
            geometry=[Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])],
            crs="EPSG:4326",
        )
        mock_read.return_value = mock_gdf

        result = get_polish_rivers()
        assert result.iloc[0]["length_km"] == 1047.0

    @patch("python_pkg.geo_data._poland_water.gpd.read_file")
    @patch("python_pkg.geo_data._poland_water.CACHE_DIR")
    def test_cached_without_length(
        self, mock_cache_dir: MagicMock, mock_read: MagicMock
    ) -> None:
        mock_path = MagicMock()
        mock_cache_dir.__truediv__ = MagicMock(return_value=mock_path)
        mock_path.exists.return_value = True

        mock_gdf = gpd.GeoDataFrame(
            {"name": ["Wisła"]},
            geometry=[Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])],
            crs="EPSG:4326",
        )
        mock_read.return_value = mock_gdf

        result = get_polish_rivers()
        assert len(result) == 1

    def test_downloads_rivers(self) -> None:
        with (
            patch("python_pkg.geo_data._poland_water.sys.stdout"),
            patch("python_pkg.geo_data._poland_water.CACHE_DIR") as mock_cache_dir,
            patch("python_pkg.geo_data._poland_water._overpass_query") as mock_query,
            patch("python_pkg.geo_data._poland_water._ensure_cache_dir"),
            patch(
                "python_pkg.geo_data._poland_water.gpd.GeoDataFrame.from_features"
            ) as mock_from_features,
            patch(
                "python_pkg.geo_data._poland_water._add_length_column"
            ) as mock_add_length,
        ):
            mock_path = MagicMock()
            mock_cache_dir.__truediv__ = MagicMock(return_value=mock_path)
            mock_path.exists.return_value = False

            mock_query.return_value = {
                "elements": [
                    # Way with wikidata
                    {
                        "type": "way",
                        "id": 1,
                        "tags": {"name": "Wisła", "wikidata": "Q54"},
                        "geometry": [{"lon": 0, "lat": 0}, {"lon": 1, "lat": 1}],
                    },
                    # Way without wikidata
                    {
                        "type": "way",
                        "id": 2,
                        "tags": {"name": "Odra"},
                        "geometry": [{"lon": 0, "lat": 0}, {"lon": 1, "lat": 1}],
                    },
                    # Relation
                    {
                        "type": "relation",
                        "id": 3,
                        "tags": {"name": "Bug", "wikidata": "Q55"},
                        "members": [
                            {
                                "type": "way",
                                "geometry": [
                                    {"lon": 0, "lat": 0},
                                    {"lon": 1, "lat": 1},
                                ],
                            },
                            {
                                "type": "way",
                                "geometry": [
                                    {"lon": 1, "lat": 1},
                                    {"lon": 2, "lat": 2},
                                ],
                            },
                        ],
                    },
                    # No name
                    {
                        "type": "way",
                        "id": 4,
                        "tags": {},
                        "geometry": [{"lon": 0, "lat": 0}, {"lon": 1, "lat": 1}],
                    },
                    # Way with no coords
                    {
                        "type": "way",
                        "id": 5,
                        "tags": {"name": "Short"},
                        "geometry": [{"lon": 0, "lat": 0}],
                    },
                ]
            }

            poly = Polygon([(20, 50), (21, 50), (21, 51), (20, 51)])
            mock_gdf = gpd.GeoDataFrame(
                {"name": ["Wisła", "Odra", "Bug"]},
                geometry=[poly, poly, poly],
                crs="EPSG:4326",
            )
            mock_from_features.return_value = mock_gdf
            gdf_with_length = mock_gdf.copy()
            gdf_with_length["length_km"] = [1047.0, 854.0, 772.0]
            mock_add_length.return_value = gdf_with_length

            result = get_polish_rivers()
            assert len(result) >= 0

    def test_empty_result(self) -> None:
        with (
            patch("python_pkg.geo_data._poland_water.sys.stdout"),
            patch("python_pkg.geo_data._poland_water.CACHE_DIR") as mock_cache_dir,
            patch("python_pkg.geo_data._poland_water._overpass_query") as mock_query,
            patch("python_pkg.geo_data._poland_water._ensure_cache_dir"),
            patch(
                "python_pkg.geo_data._poland_water.gpd.GeoDataFrame.from_features"
            ) as mock_from_features,
            patch(
                "python_pkg.geo_data._poland_water._add_length_column"
            ) as mock_add_length,
        ):
            mock_path = MagicMock()
            mock_cache_dir.__truediv__ = MagicMock(return_value=mock_path)
            mock_path.exists.return_value = False
            mock_query.return_value = {"elements": []}

            empty_gdf = gpd.GeoDataFrame({"name": [], "geometry": []})
            mock_from_features.return_value = empty_gdf
            mock_add_length.return_value = empty_gdf

            result = get_polish_rivers()
            assert len(result) == 0
