"""Tests for app_icons.fit: every glyph fills exactly the same circle."""

from __future__ import annotations

from pathlib import Path

import pytest

from python_pkg.app_icons import apps, fit, glyphs, render, style
from python_pkg.app_icons.glyphs import Glyph

SMALL = Glyph("small", "a short bar", '    <path d="M 480 512 L 544 512"/>')
NESTED = Glyph(
    "nested",
    "inner group with its own scale",
    '    <g transform="translate(400,400) scale(10)" stroke-width="{{STROKE/10}}">'
    '<path d="M 0 0 L 20 0"/></g>',
)


def _rendered_radius(glyph: Glyph, tmp_path: Path) -> tuple[float, float, float]:
    placement = fit.placement(glyph, "#FFFFFF")
    png = tmp_path / f"{glyph.name}.png"
    svg = render.build_svg(glyph, "#FFFFFF", with_background=False, offset=placement)
    render.rasterise(svg, png, style.CANVAS)
    return fit.ink_geometry(png)


class TestPlacement:
    @pytest.mark.parametrize("key", sorted(apps.APPS))
    def test_every_app_hits_the_family_radius(self, key: str, tmp_path: Path) -> None:
        glyph = glyphs.get_glyph(apps.get_app(key).glyph)
        radius, cx, cy = _rendered_radius(glyph, tmp_path)
        assert radius == pytest.approx(style.INK_RADIUS, rel=0.01)
        assert cx == pytest.approx(style.CENTRE, abs=2)
        assert cy == pytest.approx(style.CENTRE, abs=2)

    def test_tiny_glyph_is_scaled_up(self, tmp_path: Path) -> None:
        radius, _cx, _cy = _rendered_radius(SMALL, tmp_path)
        assert radius == pytest.approx(style.INK_RADIUS, rel=0.01)

    def test_stroke_weight_is_not_scaled(self) -> None:
        placement = fit.placement(SMALL, "#FFFFFF")
        svg = render.build_svg(
            SMALL, "#FFFFFF", with_background=False, offset=placement
        )
        assert placement.scale > 1
        assert f'stroke-width="{style.STROKE_WIDTH / placement.scale:g}"' in svg

    def test_nested_scale_marker_is_compensated(self) -> None:
        placement = render.Placement(0, 0, 2)
        svg = render.build_svg(
            NESTED, "#FFFFFF", with_background=False, offset=placement
        )
        assert f'stroke-width="{style.STROKE_WIDTH / 20:g}"' in svg
        assert "{{STROKE" not in svg


class TestInkGeometry:
    def test_blank_image_is_zero(self, tmp_path: Path) -> None:
        png = tmp_path / "blank.png"
        render.rasterise(
            render.build_svg(Glyph("none", "", ""), "#FFFFFF", with_background=False),
            png,
            64,
        )
        assert fit.ink_geometry(png) == (0.0, 0.0, 0.0)

    def test_empty_glyph_raises(self) -> None:
        with pytest.raises(render.EmptyGlyphError) as excinfo:
            fit.placement(Glyph("none", "", ""), "#FFFFFF")
        assert excinfo.value.name == "none"

    def test_round_cap_returns_best_effort(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(fit, "_MAX_ROUNDS", 1)
        assert fit.placement(SMALL, "#FFFFFF").scale > 1


def test_ink_circle_is_inside_android_visible_zone() -> None:
    # Android guarantees a 66dp circle (radius 33dp) survives every mask.
    assert pytest.approx(24.39, abs=0.01) == style.INK_RADIUS_DP
    assert style.INK_RADIUS_DP < 33
