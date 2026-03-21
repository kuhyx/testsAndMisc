"""Tests for the Polish islands Anki generator."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import geopandas as gpd
import matplotlib.pyplot as plt
import pytest
from shapely.geometry import Polygon

try:
    from python_pkg.anki_decks.polish_islands.polish_islands_anki import (
        _init_worker,
        _island_extends_beyond,
        _mp_state,
        _render_single_island,
        create_island_map,
        generate_anki_package,
        generate_island_image_bytes,
        main,
    )
except ImportError:
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))
    from python_pkg.anki_decks.polish_islands.polish_islands_anki import (
        _init_worker,
        _island_extends_beyond,
        _mp_state,
        _render_single_island,
        create_island_map,
        generate_anki_package,
        generate_island_image_bytes,
        main,
    )

_MOD = "python_pkg.anki_decks.polish_islands.polish_islands_anki"


def _boundary() -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        geometry=[Polygon([(14, 49), (24, 49), (24, 55), (14, 55)])],
        crs="EPSG:4326",
    )


def _island_inside() -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        [
            {
                "name": "Wyspa A",
                "area_km2": 10.0,
                "geometry": Polygon([(18, 52), (19, 52), (19, 53), (18, 53)]),
            },
        ],
        crs="EPSG:4326",
    )


def _island_outside() -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        [
            {
                "name": "Wyspa B",
                "area_km2": 20.0,
                "geometry": Polygon([(13, 52), (15, 52), (15, 53), (13, 53)]),
            },
        ],
        crs="EPSG:4326",
    )


class _FakePool:
    def __init__(self, processes=None, initializer=None, initargs=()) -> None:
        if initializer:
            initializer(*initargs)

    def imap_unordered(self, func, items):
        return [func(item) for item in items]

    def __enter__(self):
        return self

    def __exit__(self, *a):
        pass


class TestIslandExtendsBeyond:
    """Tests for _island_extends_beyond."""

    def test_inside_returns_false(self) -> None:
        assert not _island_extends_beyond(_island_inside(), _boundary())

    def test_outside_returns_true(self) -> None:
        assert _island_extends_beyond(_island_outside(), _boundary())


class TestCreateIslandMap:
    """Tests for create_island_map - all 3 branches."""

    def test_zoom_true(self) -> None:
        fig = create_island_map(_island_inside(), _boundary(), zoom=True)
        assert fig is not None
        plt.close(fig)

    def test_no_zoom_extends_beyond(self) -> None:
        fig = create_island_map(_island_outside(), _boundary(), zoom=False)
        assert fig is not None
        plt.close(fig)

    def test_no_zoom_inside(self) -> None:
        fig = create_island_map(_island_inside(), _boundary(), zoom=False)
        assert fig is not None
        plt.close(fig)


class TestGenerateIslandImageBytes:
    """Tests for generate_island_image_bytes."""

    def test_returns_bytes(self) -> None:
        data = generate_island_image_bytes(_island_inside(), _boundary(), zoom=True)
        assert isinstance(data, bytes)
        assert len(data) > 0


class TestWorkers:
    """Tests for multiprocessing worker functions."""

    def test_init_worker(self, tmp_path: Path) -> None:
        path = str(tmp_path / "boundary.geojson")
        _boundary().to_file(path, driver="GeoJSON")
        _mp_state.clear()
        _init_worker(path, "zoom")
        assert "poland_boundary" in _mp_state
        assert _mp_state["zoom_mode"] == "zoom"
        _mp_state.clear()

    def test_render_single_island(self, tmp_path: Path) -> None:
        path = str(tmp_path / "boundary.geojson")
        _boundary().to_file(path, driver="GeoJSON")
        _mp_state.clear()
        _init_worker(path, "zoom")
        geojson = _island_inside().to_json()
        name, data = _render_single_island(("Wyspa A", geojson))
        assert name == "Wyspa A"
        assert len(data) > 0
        _mp_state.clear()

    def test_render_not_initialized(self) -> None:
        _mp_state.clear()
        geojson = _island_inside().to_json()
        with pytest.raises(RuntimeError, match="Worker not initialized"):
            _render_single_island(("Wyspa A", geojson))


class TestGenerateAnkiPackage:
    """Tests for generate_anki_package."""

    def test_generates_package(self) -> None:
        with patch(f"{_MOD}.mp.Pool", _FakePool):
            package = generate_anki_package(_island_inside(), _boundary())
        assert len(package.decks) == 1
        assert len(package.decks[0].notes) == 1
        _mp_state.clear()

    def test_custom_deck_name(self) -> None:
        with patch(f"{_MOD}.mp.Pool", _FakePool):
            package = generate_anki_package(_island_inside(), _boundary(), "Custom")
        assert package.decks[0].name == "Custom"
        _mp_state.clear()

    def test_progress_reporting(self) -> None:
        islands = gpd.GeoDataFrame(
            [
                {
                    "name": f"Island{i}",
                    "area_km2": 50.0,
                    "geometry": Polygon([(18, 52), (19, 52), (19, 53), (18, 53)]),
                }
                for i in range(10)
            ],
            crs="EPSG:4326",
        )
        with (
            patch(f"{_MOD}.mp.Pool", _FakePool),
            patch(f"{_MOD}.generate_island_image_bytes", return_value=b"PNG"),
        ):
            package = generate_anki_package(islands, _boundary())
        assert len(package.decks[0].notes) == 10
        _mp_state.clear()


class TestMain:
    """Tests for the main CLI function."""

    def test_creates_output(self, tmp_path: Path) -> None:
        out = tmp_path / "out.apkg"
        with (
            patch(f"{_MOD}.get_polish_islands", return_value=_island_inside()),
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
            patch(f"{_MOD}.get_polish_islands", return_value=_island_inside()),
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
            patch(f"{_MOD}.get_polish_islands", return_value=_island_inside()),
            patch(f"{_MOD}.get_poland_boundary", return_value=_boundary()),
            patch(f"{_MOD}.generate_anki_package", side_effect=OSError("fail")),
        ):
            result = main(["--output", str(tmp_path / "out.apkg")])
        assert result == 1

    def test_help(self) -> None:
        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])
        assert exc_info.value.code == 0
