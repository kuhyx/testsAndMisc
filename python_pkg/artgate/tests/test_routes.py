"""Route generator tests.

These assert the *contract* a route must satisfy to enter the bake-off, not
that any particular icon looks good -- that is the human gate's job and cannot
be asserted in code.
"""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

import numpy as np
import pytest

from python_pkg.artgate.pixels import check_alpha_binary, check_color_count
from python_pkg.artgate.routes import vector
from python_pkg.artgate.routes.procedural import PALETTE, SIZE, _put, outline
from python_pkg.artgate.routes.shapes import DRAWINGS, draw
from python_pkg.artgate.subjects import (
    BASELINE_PASS,
    BASELINE_TOTAL,
    MAX_ROUNDS,
    SUBJECTS,
    Difficulty,
    by_name,
)

if TYPE_CHECKING:
    from pathlib import Path


class TestSubjectSet:
    """The bake-off is pinned to one subject set, or comparisons are void."""

    def test_twelve_subjects(self) -> None:
        """The set matches the measured item-icons baseline size."""
        assert len(SUBJECTS) == BASELINE_TOTAL

    def test_six_safe_six_hard(self) -> None:
        """The easy/hard split is preserved exactly."""
        safe = [s for s in SUBJECTS if s.difficulty is Difficulty.SAFE]
        assert len(safe) == BASELINE_PASS

    def test_lookup(self) -> None:
        """Subjects are addressable by name."""
        assert by_name("sword").difficulty is Difficulty.HUMAN_PRIOR

    def test_unknown_subject_raises(self) -> None:
        """A name outside the fixed set is an error, not a new subject."""
        with pytest.raises(KeyError, match="not one of"):
            by_name("dragon")

    def test_round_cap_is_evidence_backed(self) -> None:
        """Two rounds, because a third produced no measured improvement."""
        assert MAX_ROUNDS == 2

    def test_difficulty_str(self) -> None:
        """Difficulty formats bare for report tables."""
        assert f"{Difficulty.SAFE}" == "SAFE"


class TestProceduralRoute:
    """Every subject renders, and renders inside the spec."""

    def test_all_subjects_have_drawings(self) -> None:
        """No subject is silently missing from the route."""
        assert {s.name for s in SUBJECTS} == set(DRAWINGS)

    @pytest.mark.parametrize("subject", [s.name for s in SUBJECTS])
    def test_output_satisfies_pixel_spec(self, subject: str) -> None:
        """Procedural output is gate-clean by construction."""
        art = draw(subject)
        assert art.shape == (SIZE, SIZE, 4)
        assert check_alpha_binary(art) == []
        assert check_color_count(art, 32) == []

    def test_output_is_not_blank(self) -> None:
        """A route that draws nothing would pass gates vacuously."""
        assert (draw("key")[:, :, 3] == 255).sum() > 20

    def test_unknown_subject_raises(self) -> None:
        """Asking for an undrawn subject fails loudly."""
        with pytest.raises(KeyError, match="no procedural drawing"):
            draw("dragon")

    def test_out_of_bounds_writes_are_clipped(self) -> None:
        """Drawing past the canvas edge is ignored, not an error.

        Shapes are written with plain arithmetic, so a radius or offset that
        runs off the canvas must clip silently rather than raise or wrap.
        """
        canvas = np.zeros((SIZE, SIZE, 4), dtype=np.uint8)
        for x, y in ((-1, 0), (0, -1), (SIZE, 0), (0, SIZE)):
            _put(canvas, x, y, "gold")
        assert not canvas.any()

    def test_outline_surrounds_content(self) -> None:
        """Outlining adds a dark border adjacent to opaque pixels."""
        canvas = np.zeros((SIZE, SIZE, 4), dtype=np.uint8)
        canvas[10:12, 10:12, :3] = PALETTE["gold"]
        canvas[10:12, 10:12, 3] = 255
        outline(canvas)
        assert tuple(canvas[9, 10, :3]) == PALETTE["outline"]
        assert canvas[9, 10, 3] == 255


class TestVectorRoute:
    """SVG rasterisation is available and produces real output."""

    def test_all_twelve_subjects_have_shapes(self) -> None:
        """The vector cell covers the same 12 subjects as every other route.

        A cell measured on five easy subjects is not comparable to one
        measured on all twelve.
        """
        assert {s.name for s in SUBJECTS} <= set(vector.all_shapes())

    def test_unknown_shape_raises(self, tmp_path: Path) -> None:
        """An undefined vector subject fails loudly."""
        with pytest.raises(KeyError, match="no vector shape"):
            vector.render("dragon", tmp_path / "x.png")

    @pytest.mark.skipif(
        shutil.which("rsvg-convert") is None,
        reason="rsvg-convert not installed",
    )
    def test_render_writes_png(self, tmp_path: Path) -> None:
        """A rendered subject lands on disk at the requested size."""
        out = vector.render("gem", tmp_path / "gem.png", size=64)
        assert out.exists()
        assert out.stat().st_size > 0

    def test_missing_binary_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A missing rasteriser is reported, never silently skipped."""
        monkeypatch.setattr(vector.shutil, "which", lambda _: None)
        with pytest.raises(vector.RenderError, match="not installed"):
            vector.render("gem", tmp_path / "gem.png")

    def test_rasteriser_failure_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A non-zero exit from the rasteriser is surfaced."""

        class _Result:
            returncode = 1
            stderr = b"boom"

        monkeypatch.setattr(vector.shutil, "which", lambda _: "/bin/true")
        monkeypatch.setattr(vector.subprocess, "run", lambda *a, **k: _Result())
        with pytest.raises(vector.RenderError, match="failed"):
            vector.render("gem", tmp_path / "gem.png")
