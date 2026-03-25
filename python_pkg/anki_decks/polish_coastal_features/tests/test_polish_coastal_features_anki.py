"""Tests for the Polish coastal features Anki generator."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import geopandas as gpd
import matplotlib.pyplot as plt
import pytest
from shapely.geometry import LineString, Point, Polygon
from typing_extensions import Self

from python_pkg.anki_decks.polish_coastal_features import (
    polish_coastal_features_anki as _mod,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable
    from pathlib import Path

_init_worker = _mod._init_worker
_mp_state = _mod._mp_state
_render_single_feature = _mod._render_single_feature
create_coastal_map = _mod.create_coastal_map
generate_anki_package = _mod.generate_anki_package
generate_coastal_image_bytes = _mod.generate_coastal_image_bytes
main = _mod.main

_MOD = "python_pkg.anki_decks.polish_coastal_features.polish_coastal_features_anki"


def _boundary() -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        geometry=[Polygon([(14, 49), (24, 49), (24, 55), (14, 55)])],
        crs="EPSG:4326",
    )


def _polygon_feature() -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        [
            {
                "name": "Mierzeja",
                "type": "peninsula",
                "geometry": Polygon([(18, 54), (19, 54), (19, 54.5), (18, 54.5)]),
            },
        ],
        crs="EPSG:4326",
    )


def _line_feature() -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        [
            {
                "name": "Klif",
                "type": "cliff",
                "geometry": LineString([(14.5, 54.5), (15, 54.6), (15.5, 54.7)]),
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


class TestCreateCoastalMap:
    """Tests for create_coastal_map."""

    def test_polygon_geometry(self) -> None:
        fig = create_coastal_map(_polygon_feature(), _boundary())
        assert fig is not None
        plt.close(fig)

    def test_line_geometry(self) -> None:
        fig = create_coastal_map(_line_feature(), _boundary())
        assert fig is not None
        plt.close(fig)

    def test_other_geometry_type(self) -> None:
        """A Point geometry hits neither Polygon nor LineString branch."""
        feature = gpd.GeoDataFrame(
            [
                {
                    "name": "PointFeature",
                    "feature_type": "buoy",
                    "geometry": Point(17, 54.5),
                }
            ],
            crs="EPSG:4326",
        )
        fig = create_coastal_map(feature, _boundary())
        assert fig is not None
        plt.close(fig)


class TestGenerateCoastalImageBytes:
    """Tests for generate_coastal_image_bytes."""

    def test_returns_bytes(self) -> None:
        data = generate_coastal_image_bytes(_polygon_feature(), _boundary())
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

    def test_render_single_feature(self, tmp_path: Path) -> None:
        path = str(tmp_path / "boundary.geojson")
        _boundary().to_file(path, driver="GeoJSON")
        _mp_state.clear()
        _init_worker(path)
        geojson = _polygon_feature().to_json()
        name, data = _render_single_feature(("Mierzeja", geojson))
        assert name == "Mierzeja"
        assert len(data) > 0
        _mp_state.clear()

    def test_render_single_feature_not_initialized(self) -> None:
        _mp_state.clear()
        geojson = _polygon_feature().to_json()
        with pytest.raises(RuntimeError, match="Worker not initialized"):
            _render_single_feature(("Mierzeja", geojson))


class TestGenerateAnkiPackage:
    """Tests for generate_anki_package."""

    def test_generates_package(self) -> None:
        with patch(f"{_MOD}.mp.Pool", _FakePool):
            package = generate_anki_package(_polygon_feature(), _boundary())
        assert len(package.decks) == 1
        assert len(package.decks[0].notes) == 1
        _mp_state.clear()

    def test_custom_deck_name(self) -> None:
        with patch(f"{_MOD}.mp.Pool", _FakePool):
            package = generate_anki_package(_polygon_feature(), _boundary(), "Custom")
        assert package.decks[0].name == "Custom"
        _mp_state.clear()

    def test_progress_reporting(self) -> None:
        features = gpd.GeoDataFrame(
            [
                {
                    "name": f"Feature{i}",
                    "feature_type": "cliff",
                    "geometry": Polygon([(16, 54), (17, 54), (17, 55), (16, 55)]),
                }
                for i in range(10)
            ],
            crs="EPSG:4326",
        )
        with (
            patch(f"{_MOD}.mp.Pool", _FakePool),
            patch(f"{_MOD}.generate_coastal_image_bytes", return_value=b"PNG"),
        ):
            package = generate_anki_package(features, _boundary())
        assert len(package.decks[0].notes) == 10
        _mp_state.clear()


class TestMain:
    """Tests for the main CLI function."""

    def test_creates_output(self, tmp_path: Path) -> None:
        out = tmp_path / "out.apkg"
        with (
            patch(
                f"{_MOD}.get_polish_coastal_features", return_value=_polygon_feature()
            ),
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
            patch(
                f"{_MOD}.get_polish_coastal_features", return_value=_polygon_feature()
            ),
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
            patch(
                f"{_MOD}.get_polish_coastal_features", return_value=_polygon_feature()
            ),
            patch(f"{_MOD}.get_poland_boundary", return_value=_boundary()),
            patch(f"{_MOD}.generate_anki_package", side_effect=OSError("fail")),
        ):
            result = main(["--output", str(tmp_path / "out.apkg")])
        assert result == 1

    def test_help(self) -> None:
        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])
        assert exc_info.value.code == 0
