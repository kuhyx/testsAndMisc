"""Tests for python_pkg.geo_data._common module."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from shapely.geometry import (
    GeometryCollection,
    LineString,
    MultiPolygon,
    Point,
    Polygon,
)

from python_pkg.geo_data._common import (
    _build_osiedla_geometry,
    _download_github_geojson,
    _ensure_cache_dir,
    _extract_line_from_way,
    _extract_osiedla_rings,
    _extract_polygon_from_element,
    _extract_polygonal_geometry,
    _overpass_query,
    _try_single_request,
)


class TestEnsureCacheDir:
    """Tests for _ensure_cache_dir."""

    def test_creates_directory(self) -> None:
        with patch.object(Path, "mkdir") as mock_mkdir:
            _ensure_cache_dir()
            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)


class TestExtractPolygonalGeometry:
    """Tests for _extract_polygonal_geometry."""

    def test_polygon_returned_directly(self) -> None:
        poly = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
        result = _extract_polygonal_geometry(poly)
        assert result is poly

    def test_multipolygon_returned_directly(self) -> None:
        mp = MultiPolygon(
            [
                Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
                Polygon([(2, 2), (3, 2), (3, 3), (2, 3)]),
            ]
        )
        result = _extract_polygonal_geometry(mp)
        assert result is mp

    def test_geometry_collection_single_polygon(self) -> None:
        poly = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
        gc = GeometryCollection([poly, LineString([(0, 0), (1, 1)])])
        result = _extract_polygonal_geometry(gc)
        assert result is not None
        assert result.equals(poly)

    def test_geometry_collection_multiple_polygons(self) -> None:
        p1 = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
        p2 = Polygon([(2, 2), (3, 2), (3, 3), (2, 3)])
        gc = GeometryCollection([p1, p2, LineString([(0, 0), (1, 1)])])
        result = _extract_polygonal_geometry(gc)
        assert isinstance(result, MultiPolygon)

    def test_geometry_collection_with_multipolygon(self) -> None:
        p1 = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
        mp = MultiPolygon(
            [
                Polygon([(2, 2), (3, 2), (3, 3), (2, 3)]),
                Polygon([(4, 4), (5, 4), (5, 5), (4, 5)]),
            ]
        )
        gc = GeometryCollection([p1, mp])
        result = _extract_polygonal_geometry(gc)
        assert isinstance(result, MultiPolygon)

    def test_geometry_collection_no_polygons(self) -> None:
        gc = GeometryCollection([LineString([(0, 0), (1, 1)])])
        result = _extract_polygonal_geometry(gc)
        assert result is None

    def test_unsupported_geometry_type(self) -> None:
        point = Point(0, 0)
        result = _extract_polygonal_geometry(point)
        assert result is None


class TestTrySingleRequest:
    """Tests for _try_single_request."""

    @patch("python_pkg.geo_data._common.requests.post")
    @patch("python_pkg.geo_data._common.sys.stdout")
    def test_successful_request(
        self, mock_stdout: MagicMock, mock_post: MagicMock
    ) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {"elements": []}
        mock_post.return_value = mock_response

        result, error = _try_single_request("http://example.com", "query")
        assert result == {"elements": []}
        assert error is None

    @patch("python_pkg.geo_data._common.requests.post")
    @patch("python_pkg.geo_data._common.sys.stdout")
    def test_request_exception(
        self, mock_stdout: MagicMock, mock_post: MagicMock
    ) -> None:
        import requests

        mock_post.side_effect = requests.RequestException("fail")
        result, error = _try_single_request("http://example.com", "query")
        assert result is None
        assert isinstance(error, requests.RequestException)

    @patch("python_pkg.geo_data._common.requests.post")
    @patch("python_pkg.geo_data._common.sys.stdout")
    def test_invalid_response_format(
        self, mock_stdout: MagicMock, mock_post: MagicMock
    ) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {"no_elements": True}
        mock_post.return_value = mock_response

        result, error = _try_single_request("http://example.com", "query")
        assert result is None
        assert isinstance(error, ValueError)

    @patch("python_pkg.geo_data._common.requests.post")
    @patch("python_pkg.geo_data._common.sys.stdout")
    def test_non_dict_response(
        self, mock_stdout: MagicMock, mock_post: MagicMock
    ) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = [1, 2, 3]
        mock_post.return_value = mock_response

        result, error = _try_single_request("http://example.com", "query")
        assert result is None
        assert isinstance(error, ValueError)

    @patch("python_pkg.geo_data._common.requests.post")
    @patch("python_pkg.geo_data._common.sys.stdout")
    def test_value_error_on_json_parse(
        self, mock_stdout: MagicMock, mock_post: MagicMock
    ) -> None:
        mock_response = MagicMock()
        mock_response.json.side_effect = ValueError("bad json")
        mock_post.return_value = mock_response

        result, error = _try_single_request("http://example.com", "query")
        assert result is None
        assert isinstance(error, ValueError)

    @patch("python_pkg.geo_data._common.requests.post")
    @patch("python_pkg.geo_data._common.sys.stdout")
    def test_timeout_error(self, mock_stdout: MagicMock, mock_post: MagicMock) -> None:
        import requests

        mock_post.side_effect = requests.Timeout("timeout")
        result, error = _try_single_request("http://example.com", "query")
        assert result is None
        assert isinstance(error, requests.Timeout)


class TestOverpassQuery:
    """Tests for _overpass_query."""

    @patch("python_pkg.geo_data._common._try_single_request")
    def test_success_on_first_try(self, mock_req: MagicMock) -> None:
        mock_req.return_value = ({"elements": []}, None)
        result = _overpass_query("query")
        assert result == {"elements": []}

    @patch("python_pkg.geo_data._common.time.sleep")
    @patch("python_pkg.geo_data._common._try_single_request")
    @patch("python_pkg.geo_data._common.sys.stdout")
    def test_retries_then_succeeds(
        self, mock_stdout: MagicMock, mock_req: MagicMock, mock_sleep: MagicMock
    ) -> None:
        mock_req.side_effect = [
            (None, ValueError("fail1")),
            ({"elements": []}, None),
        ]
        result = _overpass_query("query")
        assert result == {"elements": []}

    @patch("python_pkg.geo_data._common.time.sleep")
    @patch("python_pkg.geo_data._common._try_single_request")
    @patch("python_pkg.geo_data._common.sys.stdout")
    def test_all_endpoints_fail(
        self, mock_stdout: MagicMock, mock_req: MagicMock, mock_sleep: MagicMock
    ) -> None:
        mock_req.return_value = (None, ValueError("fail"))
        with pytest.raises(RuntimeError, match="All Overpass API endpoints failed"):
            _overpass_query("query")


class TestDownloadGithubGeojson:
    """Tests for _download_github_geojson."""

    @patch("python_pkg.geo_data._common.gpd.read_file")
    def test_cached_file_exists(self, mock_read: MagicMock) -> None:
        mock_gdf = MagicMock()
        mock_read.return_value = mock_gdf
        cache_path = MagicMock()
        cache_path.exists.return_value = True

        result = _download_github_geojson("http://example.com/data.geojson", cache_path)
        assert result is mock_gdf
        mock_read.assert_called_once_with(cache_path)

    @patch("python_pkg.geo_data._common.gpd.GeoDataFrame.from_features")
    @patch("python_pkg.geo_data._common._ensure_cache_dir")
    @patch("python_pkg.geo_data._common.requests.get")
    @patch("python_pkg.geo_data._common.sys.stdout")
    def test_downloads_and_caches(
        self,
        mock_stdout: MagicMock,
        mock_get: MagicMock,
        mock_ensure: MagicMock,
        mock_from_features: MagicMock,
    ) -> None:
        features_data: dict[str, Any] = {
            "features": [
                {
                    "type": "Feature",
                    "properties": {"name": "test"},
                    "geometry": {"type": "Point", "coordinates": [0, 0]},
                }
            ]
        }
        mock_response = MagicMock()
        mock_response.json.return_value = features_data
        mock_get.return_value = mock_response

        mock_gdf = MagicMock()
        mock_from_features.return_value = mock_gdf

        cache_path = MagicMock()
        cache_path.exists.return_value = False

        result = _download_github_geojson(
            "https://example.com/data.geojson", cache_path
        )
        assert result is mock_gdf

    def test_unsupported_url_scheme(self) -> None:
        cache_path = MagicMock()
        cache_path.exists.return_value = False
        with pytest.raises(ValueError, match="Unsupported URL scheme"):
            _download_github_geojson("ftp://example.com/data", cache_path)


class TestExtractOsiedlaRings:
    """Tests for _extract_osiedla_rings."""

    def test_outer_and_inner_rings(self) -> None:
        element: dict[str, Any] = {
            "members": [
                {
                    "role": "outer",
                    "geometry": [
                        {"lon": 0, "lat": 0},
                        {"lon": 1, "lat": 0},
                        {"lon": 1, "lat": 1},
                        {"lon": 0, "lat": 1},
                    ],
                },
                {
                    "role": "inner",
                    "geometry": [
                        {"lon": 0.2, "lat": 0.2},
                        {"lon": 0.4, "lat": 0.2},
                        {"lon": 0.4, "lat": 0.4},
                        {"lon": 0.2, "lat": 0.4},
                    ],
                },
            ]
        }
        outer, inner = _extract_osiedla_rings(element, 4)
        assert len(outer) == 1
        assert len(inner) == 1

    def test_ring_too_short(self) -> None:
        element: dict[str, Any] = {
            "members": [
                {
                    "role": "outer",
                    "geometry": [{"lon": 0, "lat": 0}, {"lon": 1, "lat": 0}],
                }
            ]
        }
        outer, inner = _extract_osiedla_rings(element, 4)
        assert len(outer) == 0
        assert len(inner) == 0

    def test_no_geometry_in_member(self) -> None:
        element: dict[str, Any] = {"members": [{"role": "outer"}]}
        outer, inner = _extract_osiedla_rings(element, 4)
        assert len(outer) == 0
        assert len(inner) == 0

    def test_already_closed_ring(self) -> None:
        element: dict[str, Any] = {
            "members": [
                {
                    "role": "outer",
                    "geometry": [
                        {"lon": 0, "lat": 0},
                        {"lon": 1, "lat": 0},
                        {"lon": 1, "lat": 1},
                        {"lon": 0, "lat": 0},
                    ],
                }
            ]
        }
        outer, _ = _extract_osiedla_rings(element, 4)
        assert len(outer) == 1
        # Already closed, so no extra point
        assert outer[0][0] == outer[0][-1]

    def test_no_members(self) -> None:
        element: dict[str, Any] = {}
        outer, inner = _extract_osiedla_rings(element, 4)
        assert len(outer) == 0
        assert len(inner) == 0

    def test_unknown_role_ignored(self) -> None:
        element: dict[str, Any] = {
            "members": [
                {
                    "role": "label",
                    "geometry": [
                        {"lon": 0, "lat": 0},
                        {"lon": 1, "lat": 0},
                        {"lon": 1, "lat": 1},
                        {"lon": 0, "lat": 1},
                    ],
                }
            ]
        }
        outer, inner = _extract_osiedla_rings(element, 4)
        assert len(outer) == 0
        assert len(inner) == 0


class TestBuildOsiedlaGeometry:
    """Tests for _build_osiedla_geometry."""

    def test_single_outer_ring(self) -> None:
        outer = [[(0, 0), (1, 0), (1, 1), (0, 0)]]
        inner: list[list[tuple[float, float]]] = []
        result = _build_osiedla_geometry(outer, inner)
        assert result["type"] == "Polygon"

    def test_single_outer_with_inner(self) -> None:
        outer = [[(0, 0), (1, 0), (1, 1), (0, 0)]]
        inner = [[(0.2, 0.2), (0.4, 0.2), (0.4, 0.4), (0.2, 0.2)]]
        result = _build_osiedla_geometry(outer, inner)
        assert result["type"] == "Polygon"
        assert len(result["coordinates"]) == 2

    def test_multiple_outer_rings(self) -> None:
        outer = [
            [(0, 0), (1, 0), (1, 1), (0, 0)],
            [(2, 2), (3, 2), (3, 3), (2, 2)],
        ]
        inner: list[list[tuple[float, float]]] = []
        result = _build_osiedla_geometry(outer, inner)
        assert result["type"] == "MultiPolygon"


class TestExtractPolygonFromElement:
    """Tests for _extract_polygon_from_element."""

    def test_relation_with_rings(self) -> None:
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
        result = _extract_polygon_from_element(element)
        assert result is not None
        assert result["type"] == "Polygon"

    def test_relation_without_outer_rings(self) -> None:
        element: dict[str, Any] = {
            "type": "relation",
            "members": [{"role": "inner", "geometry": [{"lon": 0, "lat": 0}]}],
        }
        result = _extract_polygon_from_element(element)
        assert result is None

    def test_way_with_enough_coords(self) -> None:
        element: dict[str, Any] = {
            "type": "way",
            "geometry": [
                {"lon": 0, "lat": 0},
                {"lon": 1, "lat": 0},
                {"lon": 1, "lat": 1},
                {"lon": 0, "lat": 1},
            ],
        }
        result = _extract_polygon_from_element(element)
        assert result is not None
        assert result["type"] == "Polygon"
        # Should close the ring
        assert result["coordinates"][0][0] == result["coordinates"][0][-1]

    def test_way_already_closed(self) -> None:
        element: dict[str, Any] = {
            "type": "way",
            "geometry": [
                {"lon": 0, "lat": 0},
                {"lon": 1, "lat": 0},
                {"lon": 1, "lat": 1},
                {"lon": 0, "lat": 0},
            ],
        }
        result = _extract_polygon_from_element(element)
        assert result is not None

    def test_way_too_few_coords(self) -> None:
        element: dict[str, Any] = {
            "type": "way",
            "geometry": [{"lon": 0, "lat": 0}, {"lon": 1, "lat": 0}],
        }
        result = _extract_polygon_from_element(element)
        assert result is None

    def test_way_no_geometry(self) -> None:
        element: dict[str, Any] = {"type": "way"}
        result = _extract_polygon_from_element(element)
        assert result is None

    def test_unknown_type(self) -> None:
        element: dict[str, Any] = {"type": "node"}
        result = _extract_polygon_from_element(element)
        assert result is None


class TestExtractLineFromWay:
    """Tests for _extract_line_from_way."""

    def test_valid_way(self) -> None:
        element: dict[str, Any] = {
            "type": "way",
            "geometry": [{"lon": 0, "lat": 0}, {"lon": 1, "lat": 1}],
        }
        result = _extract_line_from_way(element)
        assert result is not None
        assert result["type"] == "LineString"

    def test_too_few_coords(self) -> None:
        element: dict[str, Any] = {
            "type": "way",
            "geometry": [{"lon": 0, "lat": 0}],
        }
        result = _extract_line_from_way(element)
        assert result is None

    def test_not_a_way(self) -> None:
        element: dict[str, Any] = {"type": "node"}
        result = _extract_line_from_way(element)
        assert result is None

    def test_way_no_geometry(self) -> None:
        element: dict[str, Any] = {"type": "way"}
        result = _extract_line_from_way(element)
        assert result is None
