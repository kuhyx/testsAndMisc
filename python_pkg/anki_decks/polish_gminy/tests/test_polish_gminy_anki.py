"""Tests for the Polish gminy Anki generator."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import geopandas as gpd
import matplotlib.pyplot as plt
import pytest
from shapely.geometry import Polygon
from typing_extensions import Self

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

try:
    from python_pkg.anki_decks.polish_gminy.polish_gminy_anki import (
        _build_color_map,
        _init_worker,
        _mp_state,
        _render_single_gmina,
        create_gmina_map,
        generate_anki_package,
        generate_gmina_image_bytes,
        main,
    )
except ImportError:
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))
    from python_pkg.anki_decks.polish_gminy.polish_gminy_anki import (
        _build_color_map,
        _init_worker,
        _mp_state,
        _render_single_gmina,
        create_gmina_map,
        generate_anki_package,
        generate_gmina_image_bytes,
        main,
    )

_MOD = "python_pkg.anki_decks.polish_gminy.polish_gminy_anki"


def _boundary() -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        geometry=[Polygon([(14, 49), (24, 49), (24, 55), (14, 55)])],
        crs="EPSG:4326",
    )


def _gminy() -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        [
            {
                "name": "Gmina A",
                "geometry": Polygon([(16, 51), (17, 51), (17, 52), (16, 52)]),
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


class TestBuildColorMap:
    """Tests for _build_color_map."""

    def test_returns_dict(self) -> None:
        result = _build_color_map(["A", "B", "C"])
        assert isinstance(result, dict)
        assert len(result) == 3

    def test_colors_are_hex(self) -> None:
        result = _build_color_map(["X"])
        assert result["X"].startswith("#")


class TestCreateGminaMap:
    """Tests for create_gmina_map."""

    def test_returns_figure(self) -> None:
        color_map = _build_color_map(["Gmina A"])
        fig = create_gmina_map("Gmina A", _gminy(), _boundary(), color_map)
        assert fig is not None
        plt.close(fig)

    def test_missing_name_uses_default(self) -> None:
        color_map = _build_color_map(["Other"])
        fig = create_gmina_map("Gmina A", _gminy(), _boundary(), color_map)
        assert fig is not None
        plt.close(fig)


class TestGenerateGminaImageBytes:
    """Tests for generate_gmina_image_bytes."""

    def test_returns_bytes(self) -> None:
        color_map = _build_color_map(["Gmina A"])
        data = generate_gmina_image_bytes("Gmina A", _gminy(), _boundary(), color_map)
        assert isinstance(data, bytes)
        assert len(data) > 0


class TestWorkers:
    """Tests for multiprocessing worker functions."""

    def test_init_worker(self, tmp_path: Path) -> None:
        path = str(tmp_path / "boundary.geojson")
        _boundary().to_file(path, driver="GeoJSON")
        _mp_state.clear()
        _init_worker(path, {"Gmina A": "#E74C3C"})
        assert "poland_boundary" in _mp_state
        assert "color_map" in _mp_state
        _mp_state.clear()

    def test_render_single_gmina(self, tmp_path: Path) -> None:
        path = str(tmp_path / "boundary.geojson")
        _boundary().to_file(path, driver="GeoJSON")
        _mp_state.clear()
        _init_worker(path, {"Gmina A": "#E74C3C"})
        geojson = _gminy().to_json()
        name, data = _render_single_gmina(("Gmina A", geojson))
        assert name == "Gmina A"
        assert len(data) > 0
        _mp_state.clear()

    def test_render_not_initialized(self) -> None:
        _mp_state.clear()
        geojson = _gminy().to_json()
        with pytest.raises(RuntimeError, match="Worker not initialized"):
            _render_single_gmina(("Gmina A", geojson))

    def test_render_no_color_map(self, tmp_path: Path) -> None:
        path = str(tmp_path / "boundary.geojson")
        _boundary().to_file(path, driver="GeoJSON")
        _mp_state.clear()
        _mp_state["poland_boundary"] = _boundary()
        geojson = _gminy().to_json()
        with pytest.raises(RuntimeError, match="Worker not initialized"):
            _render_single_gmina(("Gmina A", geojson))
        _mp_state.clear()


class TestGenerateAnkiPackage:
    """Tests for generate_anki_package."""

    def test_generates_package(self) -> None:
        with patch(f"{_MOD}.mp.Pool", _FakePool):
            package = generate_anki_package(_gminy(), _boundary())
        assert len(package.decks) == 1
        assert len(package.decks[0].notes) == 1
        _mp_state.clear()

    def test_custom_deck_name(self) -> None:
        with patch(f"{_MOD}.mp.Pool", _FakePool):
            package = generate_anki_package(_gminy(), _boundary(), "Custom")
        assert package.decks[0].name == "Custom"
        _mp_state.clear()

    def test_progress_reporting(self) -> None:
        gminy = gpd.GeoDataFrame(
            [
                {
                    "name": f"Gmina{i}",
                    "geometry": Polygon([(16, 51), (17, 51), (17, 52), (16, 52)]),
                }
                for i in range(100)
            ],
            crs="EPSG:4326",
        )
        with (
            patch(f"{_MOD}.mp.Pool", _FakePool),
            patch(f"{_MOD}.generate_gmina_image_bytes", return_value=b"PNG"),
        ):
            package = generate_anki_package(gminy, _boundary())
        assert len(package.decks[0].notes) == 100
        _mp_state.clear()


class TestMain:
    """Tests for the main CLI function."""

    def test_creates_output(self, tmp_path: Path) -> None:
        out = tmp_path / "out.apkg"
        with (
            patch(f"{_MOD}.get_polish_gminy", return_value=_gminy()),
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
            patch(f"{_MOD}.get_polish_gminy", return_value=_gminy()),
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
            patch(f"{_MOD}.get_polish_gminy", return_value=_gminy()),
            patch(f"{_MOD}.get_poland_boundary", return_value=_boundary()),
            patch(f"{_MOD}.generate_anki_package", side_effect=OSError("fail")),
        ):
            result = main(["--output", str(tmp_path / "out.apkg")])
        assert result == 1

    def test_help(self) -> None:
        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])
        assert exc_info.value.code == 0
