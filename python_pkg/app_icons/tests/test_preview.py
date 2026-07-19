"""Tests for app_icons.preview."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from python_pkg.app_icons import preview

if TYPE_CHECKING:
    from pathlib import Path

MOD = "python_pkg.app_icons.preview"


class TestBuildContactSheet:
    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.render.rasterise")
    @patch(f"{MOD}.render.centre_offset", return_value=(0.0, 0.0))
    @patch(f"{MOD}.render.resolve_tool", return_value="/usr/bin/magick")
    def test_renders_one_tile_per_app_and_three_rows(
        self,
        mock_tool: MagicMock,
        mock_offset: MagicMock,
        raster: MagicMock,
        run: MagicMock,
        tmp_path: Path,
    ) -> None:
        destination = tmp_path / "out" / "sheet.png"
        assert preview.build_contact_sheet(["todo", "workout_app"], destination) == (
            destination
        )
        assert raster.call_count == 2
        # per app: circle mask + downscale; then 3 row montages + 1 append.
        assert run.call_count == 2 * 2 + 3 + 1
        assert destination.parent.is_dir()

    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.render.rasterise")
    @patch(f"{MOD}.render.centre_offset", return_value=(0.0, 0.0))
    @patch(f"{MOD}.render.resolve_tool", return_value="/usr/bin/magick")
    def test_final_append_is_vertical(
        self,
        mock_tool: MagicMock,
        mock_offset: MagicMock,
        mock_raster: MagicMock,
        run: MagicMock,
        tmp_path: Path,
    ) -> None:
        preview.build_contact_sheet(["todo"], tmp_path / "sheet.png")
        assert "-append" in run.call_args.args[0]
