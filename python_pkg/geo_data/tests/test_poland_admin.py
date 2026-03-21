"""Tests for python_pkg.geo_data._poland_admin module."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import geopandas as gpd
from shapely.geometry import Polygon

from python_pkg.geo_data._poland_admin import (
    _get_powiaty_population,
    _query_wikidata,
    get_poland_boundary,
    get_polish_gminy,
    get_polish_powiaty,
    get_polish_wojewodztwa,
)


class TestQueryWikidata:
    """Tests for _query_wikidata."""

    @patch("python_pkg.geo_data._poland_admin.requests.get")
    def test_successful_query(self, mock_get: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": {"bindings": [{"name": {"value": "test"}}]}
        }
        mock_get.return_value = mock_response

        result = _query_wikidata("SELECT ?x WHERE {}")
        assert result == [{"name": {"value": "test"}}]
        mock_response.raise_for_status.assert_called_once()


class TestGetPowiatyPopulation:
    """Tests for _get_powiaty_population."""

    @patch("python_pkg.geo_data._poland_admin.CACHE_DIR")
    def test_cached(self, mock_cache_dir: MagicMock) -> None:
        mock_path = MagicMock()
        mock_cache_dir.__truediv__ = MagicMock(return_value=mock_path)
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = json.dumps({"Kraków": 780000})

        result = _get_powiaty_population()
        assert result == {"Kraków": 780000}

    @patch("python_pkg.geo_data._poland_admin._ensure_cache_dir")
    @patch("python_pkg.geo_data._poland_admin._query_wikidata")
    @patch("python_pkg.geo_data._poland_admin.CACHE_DIR")
    @patch("python_pkg.geo_data._poland_admin.sys.stdout")
    def test_downloads_and_caches(
        self,
        mock_stdout: MagicMock,
        mock_cache_dir: MagicMock,
        mock_query: MagicMock,
        mock_ensure: MagicMock,
    ) -> None:
        mock_path = MagicMock()
        mock_cache_dir.__truediv__ = MagicMock(return_value=mock_path)
        mock_path.exists.return_value = False

        mock_query.return_value = [
            {
                "powiatLabel": {"value": "powiat krakowski"},
                "population": {"value": "100000"},
            },
            {
                "powiatLabel": {"value": "powiat wadowicki"},
                "population": {"value": "bad_value"},
            },
            {
                "powiatLabel": {"value": ""},
                "population": {"value": "50000"},
            },
            {
                "population": {"value": "30000"},
            },
        ]

        result = _get_powiaty_population()
        assert "krakowski" in result
        mock_path.write_text.assert_called_once()

    @patch("python_pkg.geo_data._poland_admin._ensure_cache_dir")
    @patch("python_pkg.geo_data._poland_admin._query_wikidata")
    @patch("python_pkg.geo_data._poland_admin.CACHE_DIR")
    @patch("python_pkg.geo_data._poland_admin.sys.stdout")
    def test_empty_label_skipped(
        self,
        mock_stdout: MagicMock,
        mock_cache_dir: MagicMock,
        mock_query: MagicMock,
        mock_ensure: MagicMock,
    ) -> None:
        mock_path = MagicMock()
        mock_cache_dir.__truediv__ = MagicMock(return_value=mock_path)
        mock_path.exists.return_value = False

        mock_query.return_value = [
            {"powiatLabel": {"value": ""}, "population": {"value": "1000"}},
        ]

        result = _get_powiaty_population()
        assert len(result) == 0


class TestGetPolishWojewodztwa:
    """Tests for get_polish_wojewodztwa."""

    @patch("python_pkg.geo_data._poland_admin._download_github_geojson")
    def test_returns_geodataframe(self, mock_download: MagicMock) -> None:
        mock_gdf = MagicMock(spec=gpd.GeoDataFrame)
        mock_download.return_value = mock_gdf

        result = get_polish_wojewodztwa()
        assert result is mock_gdf


class TestGetPolishPowiaty:
    """Tests for get_polish_powiaty."""

    @patch("python_pkg.geo_data._poland_admin._get_powiaty_population")
    @patch("python_pkg.geo_data._poland_admin._download_github_geojson")
    def test_with_population(
        self, mock_download: MagicMock, mock_pop: MagicMock
    ) -> None:
        gdf = gpd.GeoDataFrame(
            {"nazwa": ["powiat krakowski", "powiat Wadowice", "powiat xyz", ""]},
            geometry=[
                Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
                Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
                Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
                Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
            ],
            crs="EPSG:4326",
        )
        mock_download.return_value = gdf
        mock_pop.return_value = {"krakowski": 100000, "wadowice": 50000}

        result = get_polish_powiaty()
        assert "population" in result.columns
        # krakowski matched directly
        assert result.iloc[0]["population"] == 100000
        # Wadowice matched case-insensitively
        assert result.iloc[1]["population"] == 50000


class TestGetPolishGminy:
    """Tests for get_polish_gminy."""

    @patch("python_pkg.geo_data._poland_admin.gpd.read_file")
    @patch("python_pkg.geo_data._poland_admin.CACHE_DIR")
    def test_cached_with_area(
        self, mock_cache_dir: MagicMock, mock_read: MagicMock
    ) -> None:
        mock_path = MagicMock()
        mock_cache_dir.__truediv__ = MagicMock(return_value=mock_path)
        mock_path.exists.return_value = True

        mock_gdf = gpd.GeoDataFrame(
            {
                "name": ["A", "B"],
                "area_km2": [200.0, 100.0],
            },
            geometry=[
                Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
                Polygon([(2, 2), (3, 2), (3, 3), (2, 3)]),
            ],
            crs="EPSG:4326",
        )
        mock_read.return_value = mock_gdf

        result = get_polish_gminy()
        assert result.iloc[0]["area_km2"] == 200.0

    @patch("python_pkg.geo_data._poland_admin.gpd.read_file")
    @patch("python_pkg.geo_data._poland_admin.CACHE_DIR")
    def test_cached_without_area(
        self, mock_cache_dir: MagicMock, mock_read: MagicMock
    ) -> None:
        mock_path = MagicMock()
        mock_cache_dir.__truediv__ = MagicMock(return_value=mock_path)
        mock_path.exists.return_value = True

        mock_gdf = gpd.GeoDataFrame(
            {"name": ["A"]},
            geometry=[Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])],
            crs="EPSG:4326",
        )
        mock_read.return_value = mock_gdf

        result = get_polish_gminy()
        assert len(result) == 1

    @patch("python_pkg.geo_data._common._add_area_column")
    @patch("python_pkg.geo_data._poland_admin.gpd.GeoDataFrame.from_features")
    @patch("python_pkg.geo_data._poland_admin._ensure_cache_dir")
    @patch("python_pkg.geo_data._poland_admin._overpass_query")
    @patch("python_pkg.geo_data._poland_admin.CACHE_DIR")
    @patch("python_pkg.geo_data._poland_admin.sys.stdout")
    def test_downloads_from_osm(
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
                    "type": "relation",
                    "tags": {"name": "Gmina A"},
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
                },
                # Duplicate name - should be skipped
                {
                    "type": "relation",
                    "tags": {"name": "Gmina A"},
                    "members": [
                        {
                            "role": "outer",
                            "geometry": [
                                {"lon": 2, "lat": 2},
                                {"lon": 3, "lat": 2},
                                {"lon": 3, "lat": 3},
                                {"lon": 2, "lat": 3},
                            ],
                        }
                    ],
                },
                # Not a relation - should be skipped
                {"type": "way", "tags": {"name": "Way"}},
                # No name
                {"type": "relation", "tags": {}},
                # No outer rings
                {
                    "type": "relation",
                    "tags": {"name": "Empty"},
                    "members": [],
                },
            ]
        }

        mock_gdf = gpd.GeoDataFrame(
            {"name": ["Gmina A"], "area_km2": [100.0]},
            geometry=[Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])],
            crs="EPSG:4326",
        )
        mock_from_features.return_value = mock_gdf
        mock_add_area.return_value = mock_gdf

        result = get_polish_gminy()
        assert len(result) == 1


class TestGetPolandBoundary:
    """Tests for get_poland_boundary."""

    @patch("python_pkg.geo_data._poland_admin.gpd.read_file")
    @patch("python_pkg.geo_data._poland_admin.CACHE_DIR")
    def test_cached(self, mock_cache_dir: MagicMock, mock_read: MagicMock) -> None:
        mock_path = MagicMock()
        mock_cache_dir.__truediv__ = MagicMock(return_value=mock_path)
        mock_path.exists.return_value = True

        mock_gdf = MagicMock(spec=gpd.GeoDataFrame)
        mock_read.return_value = mock_gdf

        result = get_poland_boundary()
        assert result is mock_gdf

    @patch("python_pkg.geo_data._poland_admin.gpd.GeoDataFrame.to_file")
    @patch("python_pkg.geo_data._poland_admin._ensure_cache_dir")
    @patch("python_pkg.geo_data._poland_admin.get_polish_wojewodztwa")
    @patch("python_pkg.geo_data._poland_admin.CACHE_DIR")
    def test_dissolves_from_wojewodztwa(
        self,
        mock_cache_dir: MagicMock,
        mock_woj: MagicMock,
        mock_ensure: MagicMock,
        mock_to_file: MagicMock,
    ) -> None:
        mock_path = MagicMock()
        mock_cache_dir.__truediv__ = MagicMock(return_value=mock_path)
        mock_path.exists.return_value = False

        woj_gdf = gpd.GeoDataFrame(
            {"name": ["woj1", "woj2"]},
            geometry=[
                Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
                Polygon([(1, 0), (2, 0), (2, 1), (1, 1)]),
            ],
            crs="EPSG:4326",
        )
        mock_woj.return_value = woj_gdf

        result = get_poland_boundary()
        assert len(result) == 1
