"""Tests for the Polish UNESCO sites Anki generator."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import geopandas as gpd
import matplotlib.pyplot as plt
import pytest
from shapely.geometry import Point, Polygon
from typing_extensions import Self

try:
    from python_pkg.anki_decks.polish_unesco_sites.polish_unesco_sites_anki import (
        _init_worker,
        _mp_state,
        _render_single_site,
        create_unesco_map,
        generate_anki_package,
        generate_unesco_image_bytes,
        main,
    )
except ImportError:
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))
    from python_pkg.anki_decks.polish_unesco_sites.polish_unesco_sites_anki import (
        _init_worker,
        _mp_state,
        _render_single_site,
        create_unesco_map,
        generate_anki_package,
        generate_unesco_image_bytes,
        main,
    )

_MOD = "python_pkg.anki_decks.polish_unesco_sites.polish_unesco_sites_anki"


def _boundary() -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        geometry=[Polygon([(14, 49), (24, 49), (24, 55), (14, 55)])],
        crs="EPSG:4326",
    )


def _site_point() -> gpd.GeoDataFrame:
    """UNESCO site with Point geometry."""
    return gpd.GeoDataFrame(
        [
            {
                "name": "PointSite",
                "inscribed_year": 1978,
                "category": "Cultural",
                "geometry": Point(20, 52),
            },
        ],
        crs="EPSG:4326",
    )


def _site_polygon() -> gpd.GeoDataFrame:
    """UNESCO site with Polygon geometry (centroid branch)."""
    return gpd.GeoDataFrame(
        [
            {
                "name": "PolygonSite",
                "inscribed_year": 2003,
                "category": "Natural",
                "geometry": Polygon([(19, 51), (20, 51), (20, 52), (19, 52)]),
            },
        ],
        crs="EPSG:4326",
    )


class _FakePool:
    def __init__(
        self,
        processes: int | None = None,
        initializer: Any = None,
        initargs: tuple[Any, ...] = (),
    ) -> None:
        if initializer:
            initializer(*initargs)

    def imap_unordered(
        self,
        func: Any,
        items: Any,
    ) -> list[Any]:
        return [func(item) for item in items]

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *a: object) -> None:
        pass


class TestCreateUnescoMap:
    """Tests for create_unesco_map."""

    def test_point_geometry(self) -> None:
        fig = create_unesco_map(_site_point(), _boundary())
        assert fig is not None
        plt.close(fig)

    def test_polygon_geometry_uses_centroid(self) -> None:
        fig = create_unesco_map(_site_polygon(), _boundary())
        assert fig is not None
        plt.close(fig)


class TestGenerateUnescoImageBytes:
    """Tests for generate_unesco_image_bytes."""

    def test_returns_bytes(self) -> None:
        data = generate_unesco_image_bytes(_site_point(), _boundary())
        assert isinstance(data, bytes)
        assert len(data) > 0


class TestWorkers:
    """Tests for multiprocessing worker functions."""

    def test_init_worker(self, tmp_path: Path) -> None:
        boundary = _boundary()
        path = str(tmp_path / "boundary.geojson")
        boundary.to_file(path, driver="GeoJSON")
        _mp_state.clear()
        _init_worker(path)
        assert "poland_boundary" in _mp_state
        _mp_state.clear()

    def test_render_single_site(self, tmp_path: Path) -> None:
        boundary = _boundary()
        path = str(tmp_path / "boundary.geojson")
        boundary.to_file(path, driver="GeoJSON")
        _mp_state.clear()
        _init_worker(path)
        site = _site_point()
        geojson = site.to_json()
        name, data = _render_single_site(("PointSite", geojson))
        assert name == "PointSite"
        assert len(data) > 0
        _mp_state.clear()

    def test_render_not_initialized(self) -> None:
        _mp_state.clear()
        site = _site_point()
        geojson = site.to_json()
        with pytest.raises(RuntimeError, match="Worker not initialized"):
            _render_single_site(("PointSite", geojson))


class TestGenerateAnkiPackage:
    """Tests for generate_anki_package."""

    def test_generates_package(self) -> None:
        with patch(f"{_MOD}.mp.Pool", _FakePool):
            package = generate_anki_package(_site_point(), _boundary())
        assert len(package.decks) == 1
        assert len(package.decks[0].notes) == 1
        _mp_state.clear()

    def test_custom_deck_name(self) -> None:
        with patch(f"{_MOD}.mp.Pool", _FakePool):
            package = generate_anki_package(_site_point(), _boundary(), "Custom UNESCO")
        assert package.decks[0].name == "Custom UNESCO"
        _mp_state.clear()

    def test_progress_reporting(self) -> None:
        """Use 5 items to trigger the progress reporting branch."""
        sites = gpd.GeoDataFrame(
            [
                {
                    "name": f"Site{i}",
                    "inscribed_year": 2000 + i,
                    "category": "Cultural",
                    "geometry": Point(19 + i * 0.1, 51),
                }
                for i in range(5)
            ],
            crs="EPSG:4326",
        )
        with patch(f"{_MOD}.mp.Pool", _FakePool):
            package = generate_anki_package(sites, _boundary())
        assert len(package.decks[0].notes) == 5
        _mp_state.clear()


class TestMain:
    """Tests for the main CLI function."""

    def test_creates_output(self, tmp_path: Path) -> None:
        out = tmp_path / "out.apkg"
        with (
            patch(f"{_MOD}.get_polish_unesco_sites", return_value=_site_point()),
            patch(f"{_MOD}.get_poland_boundary", return_value=_boundary()),
            patch(f"{_MOD}.mp.Pool", _FakePool),
        ):
            result = main(["--output", str(out)])
        assert result == 0
        assert out.exists()
        _mp_state.clear()

    def test_preview(self, tmp_path: Path) -> None:
        out = tmp_path / "out.apkg"
        preview = tmp_path / "preview"
        with (
            patch(f"{_MOD}.get_polish_unesco_sites", return_value=_site_point()),
            patch(f"{_MOD}.get_poland_boundary", return_value=_boundary()),
            patch(f"{_MOD}.mp.Pool", _FakePool),
        ):
            result = main(
                [
                    "--output",
                    str(out),
                    "--preview",
                    str(preview),
                    "--preview-count",
                    "1",
                ]
            )
        assert result == 0
        assert preview.exists()
        _mp_state.clear()

    def test_error_returns_1(self, tmp_path: Path) -> None:
        with (
            patch(f"{_MOD}.get_polish_unesco_sites", return_value=_site_point()),
            patch(f"{_MOD}.get_poland_boundary", return_value=_boundary()),
            patch(f"{_MOD}.generate_anki_package", side_effect=OSError("fail")),
        ):
            result = main(["--output", str(tmp_path / "out.apkg")])
        assert result == 1

    def test_help(self) -> None:
        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])
        assert exc_info.value.code == 0
