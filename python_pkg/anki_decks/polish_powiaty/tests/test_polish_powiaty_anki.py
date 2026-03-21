"""Tests for the Polish powiaty Anki generator."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import geopandas as gpd
import matplotlib.pyplot as plt
import pytest
from shapely.geometry import Polygon

try:
    from python_pkg.anki_decks.polish_powiaty.polish_powiaty_anki import (
        create_powiat_map,
        generate_anki_package,
        generate_powiat_image_bytes,
        main,
    )
except ImportError:
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))
    from python_pkg.anki_decks.polish_powiaty.polish_powiaty_anki import (
        create_powiat_map,
        generate_anki_package,
        generate_powiat_image_bytes,
        main,
    )

_MOD = "python_pkg.anki_decks.polish_powiaty.polish_powiaty_anki"


def _boundary() -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        geometry=[Polygon([(14, 49), (24, 49), (24, 55), (14, 55)])],
        crs="EPSG:4326",
    )


def _powiaty() -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        [
            {
                "nazwa": "powiat testowy",
                "geometry": Polygon([(16, 51), (17, 51), (17, 52), (16, 52)]),
            },
        ],
        crs="EPSG:4326",
    )


class TestCreatePowiatMap:
    """Tests for create_powiat_map."""

    def test_returns_figure(self) -> None:
        powiaty = _powiaty()
        fig = create_powiat_map("powiat testowy", powiaty, _boundary(), powiaty)
        assert fig is not None
        plt.close(fig)


class TestGeneratePowiatImageBytes:
    """Tests for generate_powiat_image_bytes."""

    def test_returns_bytes(self) -> None:
        powiaty = _powiaty()
        data = generate_powiat_image_bytes(
            "powiat testowy", powiaty, _boundary(), powiaty
        )
        assert isinstance(data, bytes)
        assert len(data) > 0


class TestGenerateAnkiPackage:
    """Tests for generate_anki_package."""

    def test_generates_package(self) -> None:
        package = generate_anki_package(_powiaty(), _boundary())
        assert len(package.decks) == 1
        assert len(package.decks[0].notes) == 1

    def test_custom_deck_name(self) -> None:
        package = generate_anki_package(_powiaty(), _boundary(), "Custom")
        assert package.decks[0].name == "Custom"


class TestMain:
    """Tests for the main CLI function."""

    def test_creates_output(self, tmp_path: Path) -> None:
        out = tmp_path / "out.apkg"
        with (
            patch(f"{_MOD}.get_polish_powiaty", return_value=_powiaty()),
            patch(f"{_MOD}.get_poland_boundary", return_value=_boundary()),
        ):
            result = main(["--output", str(out)])
        assert result == 0
        assert out.exists()

    def test_preview(self, tmp_path: Path) -> None:
        out = tmp_path / "out.apkg"
        preview = tmp_path / "preview"
        with (
            patch(f"{_MOD}.get_polish_powiaty", return_value=_powiaty()),
            patch(f"{_MOD}.get_poland_boundary", return_value=_boundary()),
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
            patch(f"{_MOD}.get_polish_powiaty", return_value=_powiaty()),
            patch(f"{_MOD}.get_poland_boundary", return_value=_boundary()),
            patch(f"{_MOD}.generate_anki_package", side_effect=OSError("fail")),
        ):
            result = main(["--output", str(tmp_path / "out.apkg")])
        assert result == 1

    def test_help(self) -> None:
        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])
        assert exc_info.value.code == 0
