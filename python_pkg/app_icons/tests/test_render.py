"""Tests for app_icons.render."""

from __future__ import annotations

from pathlib import Path
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from python_pkg.app_icons import render, style
from python_pkg.app_icons.glyphs import Glyph

MOD = "python_pkg.app_icons.render"

DOT = Glyph("dot", "a dot", '    <path d="M 100 100 L 200 200"/>')
FILLED = Glyph("filled", "a filled shape", '    <rect fill="{{ACCENT}}" />')


class TestResolveTool:
    @patch(f"{MOD}.shutil.which", return_value="/usr/bin/magick")
    def test_found(self, mock_which: MagicMock) -> None:
        assert render.resolve_tool("magick") == "/usr/bin/magick"

    @patch(f"{MOD}.shutil.which", return_value=None)
    def test_missing(self, mock_which: MagicMock) -> None:
        with pytest.raises(render.ToolMissingError) as excinfo:
            render.resolve_tool("nope")
        assert excinfo.value.tool == "nope"


class TestBuildSvg:
    def test_background_layer_has_field(self) -> None:
        svg = render.build_svg(DOT, "#123456", with_background=True)
        assert style.BACKGROUND in svg
        assert 'stroke="#123456"' in svg
        assert f'stroke-width="{style.STROKE_WIDTH}"' in svg

    def test_transparent_layer_has_no_field(self) -> None:
        svg = render.build_svg(DOT, "#123456", with_background=False)
        assert style.BACKGROUND not in svg

    def test_offset_is_applied(self) -> None:
        svg = render.build_svg(DOT, "#123456", with_background=False, offset=(3.5, -7))
        assert 'transform="translate(3.5,-7)"' in svg

    def test_accent_token_is_substituted(self) -> None:
        svg = render.build_svg(FILLED, "#ABCDEF", with_background=False)
        assert style.ACCENT_MARKER not in svg
        assert 'fill="#ABCDEF"' in svg


class TestRasterise:
    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.resolve_tool", return_value="/usr/bin/rsvg-convert")
    def test_invokes_rsvg_and_creates_parent(
        self, mock_tool: MagicMock, run: MagicMock, tmp_path: Path
    ) -> None:
        destination = tmp_path / "nested" / "out.png"
        render.rasterise("<svg/>", destination, 256)
        assert destination.parent.is_dir()
        argv = run.call_args.args[0]
        assert argv[0] == "/usr/bin/rsvg-convert"
        assert "256" in argv
        assert run.call_args.kwargs["input"] == b"<svg/>"


class TestInkBbox:
    @patch(f"{MOD}.subprocess.run")
    @patch(f"{MOD}.resolve_tool", return_value="/usr/bin/magick")
    def test_parses_identify_output(self, mock_tool: MagicMock, run: MagicMock) -> None:
        run.return_value = subprocess.CompletedProcess([], 0, stdout="400 300 +100 +50")
        assert render._ink_bbox(Path("x.png")) == (400, 300, 100, 50)


class TestCentreOffset:
    @patch(f"{MOD}._ink_bbox", return_value=(400, 300, 112, 262))
    @patch(f"{MOD}.rasterise")
    def test_centres_ink_box(
        self, mock_raster: MagicMock, mock_bbox: MagicMock
    ) -> None:
        dx, dy = render.centre_offset(DOT, "#FFFFFF")
        # ink centre is (312, 412); canvas centre is 512.
        assert (dx, dy) == (200, 100)

    @patch(f"{MOD}._ink_bbox", return_value=(0, 0, 0, 0))
    @patch(f"{MOD}.rasterise")
    def test_empty_glyph_raises(
        self, mock_raster: MagicMock, mock_bbox: MagicMock
    ) -> None:
        with pytest.raises(render.EmptyGlyphError) as excinfo:
            render.centre_offset(DOT, "#FFFFFF")
        assert excinfo.value.name == "dot"


class TestSafeBoxOverflow:
    @patch(f"{MOD}._ink_bbox", return_value=(600, 500, 0, 0))
    @patch(f"{MOD}.rasterise")
    def test_reports_horizontal_overflow(
        self, mock_raster: MagicMock, mock_bbox: MagicMock
    ) -> None:
        assert render.safe_box_overflow(DOT, "#FFFFFF") == (600 - style.SAFE_BOX, 0)

    @patch(f"{MOD}._ink_bbox", return_value=(100, 100, 0, 0))
    @patch(f"{MOD}.rasterise")
    def test_no_overflow_is_zero(
        self, mock_raster: MagicMock, mock_bbox: MagicMock
    ) -> None:
        assert render.safe_box_overflow(DOT, "#FFFFFF") == (0, 0)
