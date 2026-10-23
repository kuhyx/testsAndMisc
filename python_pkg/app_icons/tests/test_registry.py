"""Tests for the app registry, glyph library and family style invariants."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from PIL import Image
import pytest

from python_pkg.app_icons import apps, fit, glyphs, render, style

if TYPE_CHECKING:
    from pathlib import Path


def _centre_column_gaps(glyph_name: str, tmp_path: Path) -> list[int]:
    """Render a glyph at its FINAL fitted scale and list the transparent runs
    between inked runs down the centre column, in pixels of the 1024 canvas.
    """
    glyph = glyphs.get_glyph(glyph_name)
    placement = fit.placement(glyph, "#FFFFFF")
    png = tmp_path / f"{glyph_name}.png"
    svg = render.build_svg(glyph, "#FFFFFF", with_background=False, offset=placement)
    render.rasterise(svg, png, style.CANVAS)
    with Image.open(png) as image:
        alpha = np.asarray(image.convert("RGBA"))[:, int(style.CENTRE), 3]
    ink = alpha > 127
    edges = np.flatnonzero(np.diff(ink.astype(np.int8)))
    # edges alternate ink-end / ink-start once past the first ink run.
    ends, starts = edges[1::2], edges[2::2]
    return [int(start - end) for end, start in zip(ends, starts, strict=False)]


class TestGlyphLookup:
    def test_known_glyph(self) -> None:
        assert glyphs.get_glyph("barbell").name == "barbell"

    def test_unknown_glyph_lists_alternatives(self) -> None:
        with pytest.raises(KeyError, match="barbell"):
            glyphs.get_glyph("nope")


class TestAppLookup:
    def test_known_app(self) -> None:
        assert apps.get_app("todo").glyph == "checklist"

    def test_unknown_app_lists_alternatives(self) -> None:
        with pytest.raises(KeyError, match="todo"):
            apps.get_app("nope")

    def test_asset_dir_is_under_repo(self) -> None:
        app = apps.get_app("todo")
        assert app.asset_dir == app.repo / "assets" / "icon"


class TestFamilyInvariants:
    def test_every_app_references_a_real_glyph(self) -> None:
        for app in apps.APPS.values():
            assert app.glyph in glyphs.GLYPHS

    def test_accents_are_shared(self) -> None:
        """Every app uses the one family accent; apps differ by glyph only."""
        accents = {app.accent for app in apps.APPS.values()}
        assert accents == {"#B8862E"}

    def test_accents_are_hex_triplets(self) -> None:
        for app in apps.APPS.values():
            assert app.accent.startswith("#")
            assert len(app.accent) == 7
            int(app.accent[1:], 16)

    def test_no_glyph_is_reused(self) -> None:
        """Apps are told apart by glyph; a new app must not borrow one."""
        shared_by_design = {"track-bars"}  # kuhylog + betting_sim, pre-existing
        used = [app.glyph for app in apps.APPS.values()]
        reused = {glyph for glyph in used if used.count(glyph) > 1}
        assert reused <= shared_by_design

    def test_safe_box_fits_inside_canvas(self) -> None:
        assert style.SAFE_BOX < style.CANVAS
        assert style.MIN_NEGATIVE_SPACE == style.STROKE_WIDTH / 2

    def test_no_glyph_paints_the_background_colour(self) -> None:
        """A hole must be cut, not painted.

        ``icon_foreground`` and ``icon_monochrome`` are rendered on
        transparency, so a shape filled with ``style.BACKGROUND`` to fake a
        hole shows up as a charcoal blob on those layers instead of
        disappearing — and on the monochrome layer, which the system
        recolours, in the wrong colour entirely. Holes belong in the path as
        ``fill-rule="evenodd"`` subpaths.
        """
        for glyph in glyphs.GLYPHS.values():
            assert style.BACKGROUND.lower() not in glyph.body.lower(), (
                f"{glyph.name} paints style.BACKGROUND; cut the hole with "
                f'fill-rule="evenodd" instead'
            )


class TestHourglassGlyph:
    def test_daily_limits_uses_it(self) -> None:
        assert apps.get_app("daily_limits").glyph == "hourglass"

    def test_sand_is_filled_in_the_accent(self) -> None:
        """The sand takes the accent marker, so the monochrome layer recolours it."""
        body = glyphs.get_glyph("hourglass").body
        assert f'fill="{style.ACCENT_MARKER}"' in body
        assert 'stroke="none"' in body


class TestLightbulbGlyph:
    def test_tutor_uses_it(self) -> None:
        app = apps.get_app("tutor")
        assert app.glyph == "lightbulb"
        assert app.web_dir == app.repo / "web"

    def test_bulb_is_filled_in_the_accent(self) -> None:
        """The bulb takes the accent marker, so the monochrome layer recolours it."""
        assert f'fill="{style.ACCENT_MARKER}"' in glyphs.get_glyph("lightbulb").body


class TestHeadphonesGlyph:
    def test_tunedeck_uses_it(self) -> None:
        app = apps.get_app("tunedeck")
        assert app.glyph == "headphones"
        assert app.linux

    def test_cups_are_filled_in_the_accent(self) -> None:
        """The cups take the accent marker, so the monochrome layer recolours it."""
        body = glyphs.get_glyph("headphones").body
        assert f'fill="{style.ACCENT_MARKER}"' in body
        assert 'stroke="none"' in body


class TestPromptBubbleGlyph:
    def test_sufler_uses_it(self) -> None:
        app = apps.get_app("sufler")
        assert app.glyph == "prompt-bubble"
        assert app.linux

    def test_negative_space_at_final_scale(self, tmp_path: Path) -> None:
        """Bubble top, two text lines, bubble bottom: three gaps, none merging."""
        gaps = _centre_column_gaps("prompt-bubble", tmp_path)
        assert len(gaps) == 3
        assert min(gaps) >= style.MIN_NEGATIVE_SPACE


class TestCameraGlyph:
    def test_macro_cam_uses_it(self) -> None:
        app = apps.get_app("macro_cam")
        assert app.glyph == "camera"
        assert not app.linux

    def test_negative_space_at_final_scale(self, tmp_path: Path) -> None:
        """Hump->lens, lens hole, lens->body bottom, measured after the fit
        shrinks the glyph: the authoring-space gaps alone would overstate them.
        """
        gaps = _centre_column_gaps("camera", tmp_path)
        assert len(gaps) == 3
        assert min(gaps) >= style.MIN_NEGATIVE_SPACE
