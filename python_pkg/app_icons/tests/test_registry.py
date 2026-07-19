"""Tests for the app registry, glyph library and family style invariants."""

from __future__ import annotations

import pytest

from python_pkg.app_icons import apps, glyphs, style


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

    def test_accents_are_unique(self) -> None:
        accents = [app.accent for app in apps.APPS.values()]
        assert len(set(accents)) == len(accents)

    def test_accents_are_hex_triplets(self) -> None:
        for app in apps.APPS.values():
            assert app.accent.startswith("#")
            assert len(app.accent) == 7
            int(app.accent[1:], 16)

    def test_safe_box_fits_inside_canvas(self) -> None:
        assert style.SAFE_BOX < style.CANVAS
        assert style.MIN_NEGATIVE_SPACE == style.STROKE_WIDTH / 2
