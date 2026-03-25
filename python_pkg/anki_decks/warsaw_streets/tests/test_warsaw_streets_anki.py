"""Tests for the Warsaw streets Anki generator."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import geopandas as gpd
import matplotlib.pyplot as plt
import pytest
from shapely.geometry import LineString, Polygon

import python_pkg.anki_decks.warsaw_streets.warsaw_streets_anki as _mod_ref

try:
    from python_pkg.anki_decks.warsaw_streets.warsaw_streets_anki import (
        create_street_map,
        generate_anki_package,
        generate_street_image_bytes,
        get_unique_streets,
        load_street_data,
        main,
    )
except ImportError:
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))
    from python_pkg.anki_decks.warsaw_streets.warsaw_streets_anki import (
        create_street_map,
        generate_anki_package,
        generate_street_image_bytes,
        get_unique_streets,
        load_street_data,
        main,
    )

_MOD = "python_pkg.anki_decks.warsaw_streets.warsaw_streets_anki"

_WARSAW = Polygon([(20.8, 52.1), (21.2, 52.1), (21.2, 52.4), (20.8, 52.4)])


def _boundary() -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(geometry=[_WARSAW], crs="EPSG:4326")


def _street_gdf() -> gpd.GeoDataFrame:
    """A single street GeoDataFrame for map/image tests."""
    return gpd.GeoDataFrame(
        [
            {
                "name": "Marszalkowska",
                "geometry": LineString([(21.0, 52.2), (21.0, 52.35)]),
            },
        ],
        crs="EPSG:4326",
    )


def _street_segments_gdf() -> gpd.GeoDataFrame:
    """Street segments with various branches for get_unique_streets tests."""
    return gpd.GeoDataFrame(
        [
            # Two segments of the same long street → MultiLineString merge
            {
                "name": "Marszalkowska",
                "geometry": LineString([(21.0, 52.2), (21.0, 52.3)]),
            },
            {
                "name": "Marszalkowska",
                "geometry": LineString([(21.0, 52.3), (21.0, 52.4)]),
            },
            # Single segment street (long enough)
            {
                "name": "Nowy Swiat",
                "geometry": LineString([(21.01, 52.2), (21.01, 52.35)]),
            },
            # Short street (should be filtered out by MIN_STREET_LENGTH)
            {
                "name": "Krotka",
                "geometry": LineString([(21.02, 52.25), (21.02, 52.2501)]),
            },
            # "Unknown" name (should be filtered)
            {
                "name": "Unknown",
                "geometry": LineString([(21.03, 52.2), (21.03, 52.35)]),
            },
            # None name (should be filtered)
            {
                "name": None,
                "geometry": LineString([(21.04, 52.2), (21.04, 52.35)]),
            },
        ],
        crs="EPSG:4326",
    )


def _streets_list() -> list[tuple[str, gpd.GeoDataFrame, float]]:
    """Pre-built streets list for generate_anki_package tests."""
    return [
        ("Marszalkowska", _street_gdf(), 5000.0),
    ]


class TestGetUniqueStreets:
    """Tests for get_unique_streets."""

    def test_merges_segments_and_filters(self) -> None:
        result = get_unique_streets(_street_segments_gdf())
        names = [name for name, _, _ in result]
        # "Unknown" and None should be filtered
        assert "Unknown" not in names
        # "Krotka" should be filtered (too short)
        assert "Krotka" not in names
        # Long streets should be present
        assert "Marszalkowska" in names
        assert "Nowy Swiat" in names
        # Sorted by length descending
        lengths = [length for _, _, length in result]
        assert lengths == sorted(lengths, reverse=True)


class TestLoadStreetData:
    """Tests for load_street_data."""

    def test_with_warszawa_entry(self, tmp_path: Path) -> None:
        districts_dir = tmp_path / "warsaw_districts"
        districts_dir.mkdir()
        gdf = gpd.GeoDataFrame(
            [{"name": "Warszawa", "geometry": _WARSAW}], crs="EPSG:4326"
        )
        gdf.to_file(str(districts_dir / "warszawa-dzielnice.geojson"), driver="GeoJSON")
        fake_file = tmp_path / "subdir" / "module.py"
        fake_file.parent.mkdir(parents=True, exist_ok=True)
        fake_file.touch()
        with (
            patch.object(_mod_ref, "__file__", str(fake_file)),
            patch(f"{_MOD}.get_warsaw_streets", return_value=_street_segments_gdf()),
        ):
            streets, boundary = load_street_data()
        assert len(boundary) == 1
        assert len(streets) > 0

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
        with (
            patch.object(_mod_ref, "__file__", str(fake_file)),
            patch(f"{_MOD}.get_warsaw_streets", return_value=_street_segments_gdf()),
        ):
            _, boundary = load_street_data()
        assert len(boundary) == 1

    def test_file_not_found(self, tmp_path: Path) -> None:
        fake_file = tmp_path / "subdir" / "module.py"
        fake_file.parent.mkdir(parents=True, exist_ok=True)
        fake_file.touch()
        with (
            patch.object(_mod_ref, "__file__", str(fake_file)),
            patch(f"{_MOD}.get_warsaw_streets", return_value=_street_segments_gdf()),
            pytest.raises(FileNotFoundError),
        ):
            load_street_data()


class TestCreateStreetMap:
    """Tests for create_street_map."""

    def test_returns_figure(self) -> None:
        fig = create_street_map(_street_gdf(), _boundary())
        assert fig is not None
        plt.close(fig)


class TestGenerateStreetImageBytes:
    """Tests for generate_street_image_bytes."""

    def test_returns_bytes(self) -> None:
        data = generate_street_image_bytes(_street_gdf(), _boundary())
        assert isinstance(data, bytes)
        assert len(data) > 0


class TestGenerateAnkiPackage:
    """Tests for generate_anki_package."""

    def test_generates_package(self) -> None:
        package = generate_anki_package(_streets_list(), _boundary())
        assert len(package.decks) == 1
        assert len(package.decks[0].notes) == 1

    def test_custom_deck_name(self) -> None:
        package = generate_anki_package(_streets_list(), _boundary(), "Custom")
        assert package.decks[0].name == "Custom"


class TestMain:
    """Tests for the main CLI function."""

    def test_creates_output(self, tmp_path: Path) -> None:
        out = tmp_path / "out.apkg"
        with patch(
            f"{_MOD}.load_street_data", return_value=(_streets_list(), _boundary())
        ):
            result = main(["--output", str(out)])
        assert result == 0
        assert out.exists()

    def test_preview(self, tmp_path: Path) -> None:
        out = tmp_path / "out.apkg"
        preview = tmp_path / "preview"
        with patch(
            f"{_MOD}.load_street_data", return_value=(_streets_list(), _boundary())
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
        with patch(f"{_MOD}.load_street_data", side_effect=OSError("fail")):
            result = main(["--output", str(tmp_path / "out.apkg")])
        assert result == 1

    def test_help(self) -> None:
        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])
        assert exc_info.value.code == 0
