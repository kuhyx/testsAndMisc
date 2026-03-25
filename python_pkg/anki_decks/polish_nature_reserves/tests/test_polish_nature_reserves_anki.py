"""Tests for the Polish nature reserves Anki generator."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import geopandas as gpd
import matplotlib.pyplot as plt
import pytest
from shapely.geometry import Polygon
from typing_extensions import Self

import python_pkg.anki_decks.polish_nature_reserves.polish_nature_reserves_anki as _mod

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable
    from pathlib import Path

_init_worker = _mod._init_worker
_mp_state = _mod._mp_state
_render_single_reserve = _mod._render_single_reserve
create_reserve_map = _mod.create_reserve_map
generate_anki_package = _mod.generate_anki_package
generate_reserve_image_bytes = _mod.generate_reserve_image_bytes
main = _mod.main

_MOD = "python_pkg.anki_decks.polish_nature_reserves.polish_nature_reserves_anki"


def _boundary() -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        geometry=[Polygon([(14, 49), (24, 49), (24, 55), (14, 55)])],
        crs="EPSG:4326",
    )


def _reserves() -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        [
            {
                "name": "Rezerwat A",
                "area_km2": 0.5,
                "geometry": Polygon([(17, 51), (17.1, 51), (17.1, 51.1), (17, 51.1)]),
            },
        ],
        crs="EPSG:4326",
    )


class _FakePool:
    def __init__(
        self,
        _processes: int | None = None,
        initializer: Callable[..., object] | None = None,
        initargs: tuple[object, ...] = (),
    ) -> None:
        if initializer:
            initializer(*initargs)

    def imap_unordered(
        self,
        func: Callable[[object], object],
        items: Iterable[object],
    ) -> list[object]:
        return [func(item) for item in items]

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_args: object) -> None:
        pass


class TestCreateReserveMap:
    """Tests for create_reserve_map."""

    def test_returns_figure(self) -> None:
        fig = create_reserve_map(_reserves(), _boundary())
        assert fig is not None
        plt.close(fig)


class TestGenerateReserveImageBytes:
    """Tests for generate_reserve_image_bytes."""

    def test_returns_bytes(self) -> None:
        data = generate_reserve_image_bytes(_reserves(), _boundary())
        assert isinstance(data, bytes)
        assert len(data) > 0


class TestWorkers:
    """Tests for multiprocessing worker functions."""

    def test_init_worker(self, tmp_path: Path) -> None:
        path = str(tmp_path / "boundary.geojson")
        _boundary().to_file(path, driver="GeoJSON")
        _mp_state.clear()
        _init_worker(path)
        assert "poland_boundary" in _mp_state
        _mp_state.clear()

    def test_render_single_reserve(self, tmp_path: Path) -> None:
        path = str(tmp_path / "boundary.geojson")
        _boundary().to_file(path, driver="GeoJSON")
        _mp_state.clear()
        _init_worker(path)
        geojson = _reserves().to_json()
        name, data = _render_single_reserve(("Rezerwat A", geojson))
        assert name == "Rezerwat A"
        assert len(data) > 0
        _mp_state.clear()

    def test_render_not_initialized(self) -> None:
        _mp_state.clear()
        geojson = _reserves().to_json()
        with pytest.raises(RuntimeError, match="Worker not initialized"):
            _render_single_reserve(("Rezerwat A", geojson))


class TestGenerateAnkiPackage:
    """Tests for generate_anki_package."""

    def test_generates_package(self) -> None:
        with patch(f"{_MOD}.mp.Pool", _FakePool):
            package = generate_anki_package(_reserves(), _boundary())
        assert len(package.decks) == 1
        assert len(package.decks[0].notes) == 1
        _mp_state.clear()

    def test_custom_deck_name(self) -> None:
        with patch(f"{_MOD}.mp.Pool", _FakePool):
            package = generate_anki_package(_reserves(), _boundary(), "Custom")
        assert package.decks[0].name == "Custom"
        _mp_state.clear()

    def test_progress_reporting(self) -> None:
        reserves = gpd.GeoDataFrame(
            [
                {
                    "name": f"Reserve{i}",
                    "area_km2": 50.0,
                    "geometry": Polygon([(17, 51), (18, 51), (18, 52), (17, 52)]),
                }
                for i in range(100)
            ],
            crs="EPSG:4326",
        )
        with (
            patch(f"{_MOD}.mp.Pool", _FakePool),
            patch(f"{_MOD}.generate_reserve_image_bytes", return_value=b"PNG"),
        ):
            package = generate_anki_package(reserves, _boundary())
        assert len(package.decks[0].notes) == 100
        _mp_state.clear()


class TestMain:
    """Tests for the main CLI function."""

    def test_creates_output(self, tmp_path: Path) -> None:
        out = tmp_path / "out.apkg"
        with (
            patch(f"{_MOD}.get_polish_nature_reserves", return_value=_reserves()),
            patch(f"{_MOD}.get_poland_boundary", return_value=_boundary()),
            patch(f"{_MOD}.mp.Pool", _FakePool),
        ):
            result = main(["--output", str(out)])
        assert result == 0
        assert out.exists()
        _mp_state.clear()

    def test_limit(self, tmp_path: Path) -> None:
        out = tmp_path / "out.apkg"
        with (
            patch(f"{_MOD}.get_polish_nature_reserves", return_value=_reserves()),
            patch(f"{_MOD}.get_poland_boundary", return_value=_boundary()),
            patch(f"{_MOD}.mp.Pool", _FakePool),
        ):
            result = main(["--output", str(out), "--limit", "1"])
        assert result == 0
        _mp_state.clear()

    def test_preview(self, tmp_path: Path) -> None:
        out = tmp_path / "out.apkg"
        preview = tmp_path / "preview"
        with (
            patch(f"{_MOD}.get_polish_nature_reserves", return_value=_reserves()),
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
            patch(f"{_MOD}.get_polish_nature_reserves", return_value=_reserves()),
            patch(f"{_MOD}.get_poland_boundary", return_value=_boundary()),
            patch(f"{_MOD}.generate_anki_package", side_effect=OSError("fail")),
        ):
            result = main(["--output", str(tmp_path / "out.apkg")])
        assert result == 1

    def test_help(self) -> None:
        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])
        assert exc_info.value.code == 0
