"""Tests for the Polish mountain peaks Anki generator."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import geopandas as gpd
import matplotlib.pyplot as plt
import pytest
from shapely.geometry import Point, Polygon

try:
    from python_pkg.anki_decks.polish_mountain_peaks.polish_mountain_peaks_anki import (
        _init_worker,
        _mp_state,
        _render_single_peak,
        create_peak_map,
        generate_anki_package,
        generate_peak_image_bytes,
        main,
    )
except ImportError:
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))
    from python_pkg.anki_decks.polish_mountain_peaks.polish_mountain_peaks_anki import (
        _init_worker,
        _mp_state,
        _render_single_peak,
        create_peak_map,
        generate_anki_package,
        generate_peak_image_bytes,
        main,
    )

_MOD = "python_pkg.anki_decks.polish_mountain_peaks.polish_mountain_peaks_anki"


def _boundary() -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        geometry=[Polygon([(14, 49), (24, 49), (24, 55), (14, 55)])],
        crs="EPSG:4326",
    )


def _peaks() -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        [
            {
                "name": "Rysy",
                "elevation": 2499,
                "geometry": Point(20.088, 49.179),
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


class TestCreatePeakMap:
    """Tests for create_peak_map."""

    def test_zoom_true(self) -> None:
        fig = create_peak_map(_peaks(), _boundary(), zoom=True)
        assert fig is not None
        plt.close(fig)

    def test_zoom_false(self) -> None:
        fig = create_peak_map(_peaks(), _boundary(), zoom=False)
        assert fig is not None
        plt.close(fig)


class TestGeneratePeakImageBytes:
    """Tests for generate_peak_image_bytes."""

    def test_returns_bytes(self) -> None:
        data = generate_peak_image_bytes(_peaks(), _boundary(), zoom=True)
        assert isinstance(data, bytes)
        assert len(data) > 0


class TestWorkers:
    """Tests for multiprocessing worker functions."""

    def test_init_worker(self, tmp_path: Path) -> None:
        path = str(tmp_path / "boundary.geojson")
        _boundary().to_file(path, driver="GeoJSON")
        _mp_state.clear()
        _init_worker(path, "zoom")
        assert _mp_state["zoom"] is True
        _mp_state.clear()

    def test_render_single_peak(self, tmp_path: Path) -> None:
        path = str(tmp_path / "boundary.geojson")
        _boundary().to_file(path, driver="GeoJSON")
        _mp_state.clear()
        _init_worker(path, "zoom")
        geojson = _peaks().to_json()
        name, data = _render_single_peak(("Rysy", geojson))
        assert name == "Rysy"
        assert len(data) > 0
        _mp_state.clear()

    def test_render_not_initialized(self) -> None:
        _mp_state.clear()
        geojson = _peaks().to_json()
        with pytest.raises(RuntimeError, match="Worker not initialized"):
            _render_single_peak(("Rysy", geojson))


class TestGenerateAnkiPackage:
    """Tests for generate_anki_package."""

    def test_generates_package(self) -> None:
        with patch(f"{_MOD}.mp.Pool", _FakePool):
            package = generate_anki_package(_peaks(), _boundary())
        assert len(package.decks) == 1
        assert len(package.decks[0].notes) == 1
        _mp_state.clear()

    def test_custom_deck_name(self) -> None:
        with patch(f"{_MOD}.mp.Pool", _FakePool):
            package = generate_anki_package(_peaks(), _boundary(), "Custom")
        assert package.decks[0].name == "Custom"
        _mp_state.clear()

    def test_progress_reporting(self) -> None:
        peaks = gpd.GeoDataFrame(
            [
                {
                    "name": f"Peak{i}",
                    "elevation": 1000 + i,
                    "geometry": Point(19 + i * 0.01, 50),
                }
                for i in range(50)
            ],
            crs="EPSG:4326",
        )
        with (
            patch(f"{_MOD}.mp.Pool", _FakePool),
            patch(f"{_MOD}.generate_peak_image_bytes", return_value=b"PNG"),
        ):
            package = generate_anki_package(peaks, _boundary())
        assert len(package.decks[0].notes) == 50
        _mp_state.clear()


class TestMain:
    """Tests for the main CLI function."""

    def test_creates_output(self, tmp_path: Path) -> None:
        out = tmp_path / "out.apkg"
        with (
            patch(f"{_MOD}.get_polish_mountain_peaks", return_value=_peaks()),
            patch(f"{_MOD}.get_poland_boundary", return_value=_boundary()),
            patch(f"{_MOD}.mp.Pool", _FakePool),
        ):
            result = main(["--output", str(out)])
        assert result == 0
        assert out.exists()
        _mp_state.clear()

    def test_no_zoom(self, tmp_path: Path) -> None:
        out = tmp_path / "out.apkg"
        with (
            patch(f"{_MOD}.get_polish_mountain_peaks", return_value=_peaks()),
            patch(f"{_MOD}.get_poland_boundary", return_value=_boundary()),
            patch(f"{_MOD}.mp.Pool", _FakePool),
        ):
            result = main(["--output", str(out), "--no-zoom"])
        assert result == 0
        _mp_state.clear()

    def test_limit(self, tmp_path: Path) -> None:
        out = tmp_path / "out.apkg"
        with (
            patch(f"{_MOD}.get_polish_mountain_peaks", return_value=_peaks()),
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
            patch(f"{_MOD}.get_polish_mountain_peaks", return_value=_peaks()),
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
            patch(f"{_MOD}.get_polish_mountain_peaks", return_value=_peaks()),
            patch(f"{_MOD}.get_poland_boundary", return_value=_boundary()),
            patch(f"{_MOD}.generate_anki_package", side_effect=OSError("fail")),
        ):
            result = main(["--output", str(tmp_path / "out.apkg")])
        assert result == 1

    def test_help(self) -> None:
        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])
        assert exc_info.value.code == 0
