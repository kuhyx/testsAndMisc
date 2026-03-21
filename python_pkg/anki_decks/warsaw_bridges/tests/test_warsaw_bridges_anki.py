"""Tests for the Warsaw bridges Anki generator."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import geopandas as gpd
import matplotlib.pyplot as plt
import pytest
from shapely.geometry import LineString, Polygon

import python_pkg.anki_decks.warsaw_bridges.warsaw_bridges_anki as _mod_ref

try:
    from python_pkg.anki_decks.warsaw_bridges.warsaw_bridges_anki import (
        create_bridge_map,
        generate_anki_package,
        generate_bridge_image_bytes,
        load_warsaw_boundary,
        main,
    )
except ImportError:
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))
    from python_pkg.anki_decks.warsaw_bridges.warsaw_bridges_anki import (
        create_bridge_map,
        generate_anki_package,
        generate_bridge_image_bytes,
        load_warsaw_boundary,
        main,
    )

_MOD = "python_pkg.anki_decks.warsaw_bridges.warsaw_bridges_anki"

_WARSAW = Polygon([(20.8, 52.1), (21.2, 52.1), (21.2, 52.4), (20.8, 52.4)])


def _boundary() -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(geometry=[_WARSAW], crs="EPSG:4326")


def _bridges() -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        [
            {
                "name": "Most Testowy",
                "geometry": LineString([(20.9, 52.25), (21.1, 52.25)]),
            },
        ],
        crs="EPSG:4326",
    )


def _vistula() -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        geometry=[LineString([(21.0, 52.1), (21.0, 52.4)])],
        crs="EPSG:4326",
    )


class TestLoadWarsawBoundary:
    """Tests for load_warsaw_boundary."""

    def test_with_warszawa_entry(self, tmp_path: Path) -> None:
        districts_dir = tmp_path / "warsaw_districts"
        districts_dir.mkdir()
        gdf = gpd.GeoDataFrame(
            [{"name": "Warszawa", "geometry": _WARSAW}],
            crs="EPSG:4326",
        )
        gdf.to_file(str(districts_dir / "warszawa-dzielnice.geojson"), driver="GeoJSON")
        fake_file = tmp_path / "subdir" / "module.py"
        fake_file.parent.mkdir(parents=True, exist_ok=True)
        fake_file.touch()
        with patch.object(_mod_ref, "__file__", str(fake_file)):
            result = load_warsaw_boundary()
        assert len(result) == 1

    def test_without_warszawa_dissolves(self, tmp_path: Path) -> None:
        districts_dir = tmp_path / "warsaw_districts"
        districts_dir.mkdir()
        gdf = gpd.GeoDataFrame(
            [
                {
                    "name": "Mokotow",
                    "geometry": Polygon(
                        [
                            (20.8, 52.1),
                            (21.0, 52.1),
                            (21.0, 52.3),
                            (20.8, 52.3),
                        ]
                    ),
                },
            ],
            crs="EPSG:4326",
        )
        gdf.to_file(str(districts_dir / "warszawa-dzielnice.geojson"), driver="GeoJSON")
        fake_file = tmp_path / "subdir" / "module.py"
        fake_file.parent.mkdir(parents=True, exist_ok=True)
        fake_file.touch()
        with patch.object(_mod_ref, "__file__", str(fake_file)):
            result = load_warsaw_boundary()
        assert len(result) == 1

    def test_file_not_found(self, tmp_path: Path) -> None:
        fake_file = tmp_path / "subdir" / "module.py"
        fake_file.parent.mkdir(parents=True, exist_ok=True)
        fake_file.touch()
        with (
            patch.object(_mod_ref, "__file__", str(fake_file)),
            pytest.raises(FileNotFoundError),
        ):
            load_warsaw_boundary()


class TestCreateBridgeMap:
    """Tests for create_bridge_map."""

    def test_returns_figure(self) -> None:
        fig = create_bridge_map(_bridges(), _boundary(), _vistula())
        assert fig is not None
        plt.close(fig)


class TestGenerateBridgeImageBytes:
    """Tests for generate_bridge_image_bytes."""

    def test_returns_bytes(self) -> None:
        data = generate_bridge_image_bytes(_bridges(), _boundary(), _vistula())
        assert isinstance(data, bytes)
        assert len(data) > 0


class TestGenerateAnkiPackage:
    """Tests for generate_anki_package."""

    def test_generates_package(self) -> None:
        package = generate_anki_package(_bridges(), _boundary(), _vistula())
        assert len(package.decks) == 1
        assert len(package.decks[0].notes) == 1

    def test_custom_deck_name(self) -> None:
        package = generate_anki_package(_bridges(), _boundary(), _vistula(), "Custom")
        assert package.decks[0].name == "Custom"


class TestMain:
    """Tests for the main CLI function."""

    def test_creates_output(self, tmp_path: Path) -> None:
        out = tmp_path / "out.apkg"
        with (
            patch(f"{_MOD}.get_warsaw_bridges", return_value=_bridges()),
            patch(f"{_MOD}.get_vistula_river", return_value=_vistula()),
            patch(f"{_MOD}.load_warsaw_boundary", return_value=_boundary()),
        ):
            result = main(["--output", str(out)])
        assert result == 0
        assert out.exists()

    def test_preview(self, tmp_path: Path) -> None:
        out = tmp_path / "out.apkg"
        preview = tmp_path / "preview"
        with (
            patch(f"{_MOD}.get_warsaw_bridges", return_value=_bridges()),
            patch(f"{_MOD}.get_vistula_river", return_value=_vistula()),
            patch(f"{_MOD}.load_warsaw_boundary", return_value=_boundary()),
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

    def test_error_returns_1(self, tmp_path: Path) -> None:
        with (
            patch(f"{_MOD}.get_warsaw_bridges", return_value=_bridges()),
            patch(f"{_MOD}.get_vistula_river", return_value=_vistula()),
            patch(f"{_MOD}.load_warsaw_boundary", return_value=_boundary()),
            patch(f"{_MOD}.generate_anki_package", side_effect=OSError("fail")),
        ):
            result = main(["--output", str(tmp_path / "out.apkg")])
        assert result == 1

    def test_help(self) -> None:
        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])
        assert exc_info.value.code == 0
