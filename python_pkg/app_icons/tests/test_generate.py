"""Tests for app_icons.generate."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from python_pkg.app_icons import generate, style
from python_pkg.app_icons.apps import AppIcon

if TYPE_CHECKING:
    from pathlib import Path

MOD = "python_pkg.app_icons.generate"


def _app(tmp_path: Path, *, linux: bool = False) -> AppIcon:
    return AppIcon(
        key="demo",
        repo=tmp_path / "demo",
        accent="#26A69A",
        glyph="barbell",
        icon_name="demo",
        linux=linux,
    )


class TestWriteAssets:
    @patch(f"{MOD}.render.rasterise")
    @patch(f"{MOD}.render.centre_offset", return_value=(1.0, 2.0))
    def test_writes_three_svg_png_pairs(
        self, mock_offset: MagicMock, raster: MagicMock, tmp_path: Path
    ) -> None:
        written = generate.write_assets(_app(tmp_path))
        stems = sorted({path.stem for path in written})
        assert stems == ["icon", "icon_foreground", "icon_monochrome"]
        assert len(written) == 6
        assert raster.call_count == 3

    @patch(f"{MOD}.render.rasterise")
    @patch(f"{MOD}.render.centre_offset", return_value=(0.0, 0.0))
    def test_only_the_base_layer_has_the_field(
        self, mock_offset: MagicMock, mock_raster: MagicMock, tmp_path: Path
    ) -> None:
        app = _app(tmp_path)
        generate.write_assets(app)
        base = (app.asset_dir / "icon.svg").read_text(encoding="utf-8")
        foreground = (app.asset_dir / "icon_foreground.svg").read_text(encoding="utf-8")
        assert style.BACKGROUND in base
        assert style.BACKGROUND not in foreground

    @patch(f"{MOD}.render.rasterise")
    @patch(f"{MOD}.render.centre_offset", return_value=(0.0, 0.0))
    def test_monochrome_layer_is_white(
        self, mock_offset: MagicMock, mock_raster: MagicMock, tmp_path: Path
    ) -> None:
        app = _app(tmp_path)
        generate.write_assets(app)
        mono = (app.asset_dir / "icon_monochrome.svg").read_text(encoding="utf-8")
        assert f'stroke="{style.MONOCHROME}"' in mono
        assert app.accent not in mono


class TestWriteLinuxIcons:
    @patch(f"{MOD}.render.rasterise")
    @patch(f"{MOD}.render.centre_offset", return_value=(0.0, 0.0))
    def test_one_png_per_hicolor_size(
        self, mock_offset: MagicMock, raster: MagicMock, tmp_path: Path
    ) -> None:
        written = generate.write_linux_icons(_app(tmp_path, linux=True), tmp_path / "h")
        assert len(written) == len(style.LINUX_ICON_SIZES)
        assert raster.call_count == len(style.LINUX_ICON_SIZES)
        assert written[0] == tmp_path / "h" / "16" / "demo.png"


class TestRunFlutterLauncherIcons:
    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.render.resolve_tool", return_value="/usr/bin/dart")
    def test_invokes_dart_in_the_repo(
        self, mock_tool: MagicMock, run: MagicMock, tmp_path: Path
    ) -> None:
        app = _app(tmp_path)
        generate.run_flutter_launcher_icons(app)
        assert run.call_args.args[0] == [
            "/usr/bin/dart",
            "run",
            "flutter_launcher_icons",
        ]
        assert run.call_args.kwargs["cwd"] == app.repo
