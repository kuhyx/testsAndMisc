"""Tests for the Polish rivers Anki generator."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import geopandas as gpd
import matplotlib.pyplot as plt
import pytest
from shapely.geometry import LineString, Polygon
from typing_extensions import Self

try:
    from python_pkg.anki_decks.polish_rivers.polish_rivers_anki import (
        _init_worker,
        _mp_state,
        _render_single_river,
        create_river_map,
        generate_anki_package,
        generate_river_image_bytes,
        main,
    )
except ImportError:
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))
    from python_pkg.anki_decks.polish_rivers.polish_rivers_anki import (
        _init_worker,
        _mp_state,
        _render_single_river,
        create_river_map,
        generate_anki_package,
        generate_river_image_bytes,
        main,
    )

_MOD = "python_pkg.anki_decks.polish_rivers.polish_rivers_anki"


def _boundary() -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        geometry=[Polygon([(14, 49), (24, 49), (24, 55), (14, 55)])],
        crs="EPSG:4326",
    )


def _river_inside() -> gpd.GeoDataFrame:
    """River that fits inside Poland."""
    return gpd.GeoDataFrame(
        [
            {
                "name": "TestRiver",
                "length_km": 150.0,
                "geometry": LineString([(18, 51), (19, 52), (20, 53)]),
            },
        ],
        crs="EPSG:4326",
    )


def _river_outside() -> gpd.GeoDataFrame:
    """River that extends beyond Poland's borders."""
    return gpd.GeoDataFrame(
        [
            {
                "name": "BigRiver",
                "length_km": 800.0,
                "geometry": LineString([(13, 51), (18, 52), (25, 53)]),
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


class TestCreateRiverMap:
    """Tests for create_river_map."""

    def test_river_inside_poland(self) -> None:
        fig = create_river_map(_river_inside(), _boundary())
        assert fig is not None
        plt.close(fig)

    def test_river_extends_beyond(self) -> None:
        fig = create_river_map(_river_outside(), _boundary())
        assert fig is not None
        plt.close(fig)


class TestGenerateRiverImageBytes:
    """Tests for generate_river_image_bytes."""

    def test_returns_bytes(self) -> None:
        data = generate_river_image_bytes(_river_inside(), _boundary())
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

    def test_render_single_river(self, tmp_path: Path) -> None:
        boundary = _boundary()
        path = str(tmp_path / "boundary.geojson")
        boundary.to_file(path, driver="GeoJSON")
        _mp_state.clear()
        _init_worker(path)
        river = _river_inside()
        geojson = river.to_json()
        name, data = _render_single_river(("TestRiver", geojson))
        assert name == "TestRiver"
        assert len(data) > 0
        _mp_state.clear()

    def test_render_not_initialized(self) -> None:
        _mp_state.clear()
        river = _river_inside()
        geojson = river.to_json()
        with pytest.raises(RuntimeError, match="Worker not initialized"):
            _render_single_river(("TestRiver", geojson))


class TestGenerateAnkiPackage:
    """Tests for generate_anki_package."""

    def test_generates_package(self) -> None:
        with patch(f"{_MOD}.mp.Pool", _FakePool):
            package = generate_anki_package(_river_inside(), _boundary())
        assert len(package.decks) == 1
        assert len(package.decks[0].notes) == 1
        _mp_state.clear()

    def test_custom_deck_name(self) -> None:
        with patch(f"{_MOD}.mp.Pool", _FakePool):
            package = generate_anki_package(
                _river_inside(), _boundary(), "Custom Rivers"
            )
        assert package.decks[0].name == "Custom Rivers"
        _mp_state.clear()

    def test_progress_reporting(self) -> None:
        """Use 50 items to trigger the progress reporting branch."""
        rivers = gpd.GeoDataFrame(
            [
                {
                    "name": f"River{i}",
                    "length_km": 100.0 + i,
                    "geometry": LineString([(18, 51 + i * 0.01), (19, 52)]),
                }
                for i in range(50)
            ],
            crs="EPSG:4326",
        )
        with patch(f"{_MOD}.mp.Pool", _FakePool):
            package = generate_anki_package(rivers, _boundary())
        assert len(package.decks[0].notes) == 50
        _mp_state.clear()


class TestMain:
    """Tests for the main CLI function."""

    def test_creates_output(self, tmp_path: Path) -> None:
        out = tmp_path / "out.apkg"
        with (
            patch(f"{_MOD}.get_polish_rivers", return_value=_river_inside()),
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
            patch(f"{_MOD}.get_polish_rivers", return_value=_river_inside()),
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
            patch(f"{_MOD}.get_polish_rivers", return_value=_river_inside()),
            patch(f"{_MOD}.get_poland_boundary", return_value=_boundary()),
            patch(f"{_MOD}.generate_anki_package", side_effect=OSError("fail")),
        ):
            result = main(["--output", str(tmp_path / "out.apkg")])
        assert result == 1

    def test_help(self) -> None:
        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])
        assert exc_info.value.code == 0
