"""Tests for _add_area_column and _add_length_column (non-empty GDFs)."""

from __future__ import annotations

import geopandas as gpd
from shapely.geometry import LineString, Polygon

from python_pkg.geo_data._common import _add_area_column, _add_length_column


class TestAddAreaColumnNonEmpty:
    """Tests for _add_area_column with non-empty GeoDataFrame."""

    def test_adds_area_column(self) -> None:
        gdf = gpd.GeoDataFrame(
            {"name": ["A"]},
            geometry=[Polygon([(20, 50), (21, 50), (21, 51), (20, 51)])],
            crs="EPSG:4326",
        )
        result = _add_area_column(gdf)
        assert "area_km2" in result.columns
        assert result["area_km2"].iloc[0] > 0


class TestAddLengthColumnNonEmpty:
    """Tests for _add_length_column with non-empty GeoDataFrame."""

    def test_adds_length_column(self) -> None:
        gdf = gpd.GeoDataFrame(
            {"name": ["A"]},
            geometry=[LineString([(20, 50), (21, 51)])],
            crs="EPSG:4326",
        )
        result = _add_length_column(gdf)
        assert "length_km" in result.columns
        assert result["length_km"].iloc[0] > 0


class TestAddAreaColumnEmpty:
    """Tests for _add_area_column with empty GeoDataFrame."""

    def test_returns_empty_gdf(self) -> None:
        gdf = gpd.GeoDataFrame({"name": [], "geometry": []})
        result = _add_area_column(gdf)
        assert len(result) == 0


class TestAddLengthColumnEmpty:
    """Tests for _add_length_column with empty GeoDataFrame."""

    def test_returns_empty_gdf(self) -> None:
        gdf = gpd.GeoDataFrame({"name": [], "geometry": []})
        result = _add_length_column(gdf)
        assert len(result) == 0
