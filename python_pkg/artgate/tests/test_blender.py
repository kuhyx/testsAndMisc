"""Blender route tests.

The important one is ``test_exit_zero_without_output_raises``: Blender exits 0
even when the embedded script raises, so a return-code check alone reports a
phantom success. That was measured, not hypothesised -- a wrong render-engine
enum on Blender 5.2 produced exit 0 and no file.
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import pytest

from python_pkg.artgate.routes import blender
from python_pkg.artgate.routes.blender_scene import (
    RENDER_SIZE,
    SUBJECTS_3D,
    scene_script,
)

if TYPE_CHECKING:
    from pathlib import Path


class _Result:
    """Stand-in for a completed subprocess."""

    def __init__(self, returncode: int = 0, stderr: bytes = b"") -> None:
        """Store the fields the caller inspects.

        Args:
            returncode: Simulated exit status.
            stderr: Simulated error output.
        """
        self.returncode = returncode
        self.stderr = stderr


class TestSceneScript:
    """The generated scene script is well-formed and parameterised."""

    def test_render_size_is_substituted(self) -> None:
        """The template takes the requested resolution."""
        assert "resolution_x = 128" in scene_script(128)

    def test_default_size(self) -> None:
        """The default matches the documented constant."""
        assert f"resolution_x = {RENDER_SIZE}" in scene_script()

    def test_every_subject_has_a_builder(self) -> None:
        """No 3D subject is silently missing a mesh."""
        script = scene_script()
        for name in SUBJECTS_3D:
            assert f'"{name}": build_' in script

    def test_script_is_valid_python(self) -> None:
        """The emitted template compiles, so a typo fails here not in Blender."""
        compile(scene_script(), "<scene>", "exec")

    def test_transparent_film(self) -> None:
        """Icons need an alpha channel, not a background."""
        assert "film_transparent = True" in scene_script()


class TestRenderErrors:
    """Every failure mode is surfaced, never silently skipped."""

    def test_unknown_subject_raises(self, tmp_path: Path) -> None:
        """A subject with no mesh fails loudly."""
        with pytest.raises(KeyError, match="no 3D scene"):
            blender.render("dragon", tmp_path / "x.png")

    def test_missing_binary_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A missing Blender is reported rather than treated as zero output."""
        monkeypatch.setattr(blender.shutil, "which", lambda _: None)
        with pytest.raises(blender.BlenderError, match="not installed"):
            blender.render("coin", tmp_path / "x.png")

    def test_nonzero_exit_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A hard failure is surfaced with Blender's own message."""
        monkeypatch.setattr(blender.shutil, "which", lambda _: "/bin/true")
        monkeypatch.setattr(
            blender.subprocess,
            "run",
            lambda *a, **k: _Result(returncode=1, stderr=b"bad mesh"),
        )
        with pytest.raises(blender.BlenderError, match="bad mesh"):
            blender.render("coin", tmp_path / "x.png")

    def test_exit_zero_without_output_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Exit 0 with no file is a failure, not a success.

        Regression for the measured Blender 5.2 behaviour: an exception inside
        the embedded script still exits 0. Without this check the route would
        report a phantom success and the cell would score a false zero.
        """
        monkeypatch.setattr(blender.shutil, "which", lambda _: "/bin/true")
        monkeypatch.setattr(
            blender.subprocess,
            "run",
            lambda *a, **k: _Result(returncode=0, stderr=b"enum not found"),
        )
        with pytest.raises(blender.BlenderError, match="wrote no file"):
            blender.render("coin", tmp_path / "missing.png")

    def test_timeout_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A hung render is bounded, not waited on forever."""

        def _boom(*_args: object, **_kwargs: object) -> _Result:
            raise subprocess.TimeoutExpired(cmd="blender", timeout=1)

        monkeypatch.setattr(blender.shutil, "which", lambda _: "/bin/true")
        monkeypatch.setattr(blender.subprocess, "run", _boom)
        with pytest.raises(blender.BlenderError, match="timed out"):
            blender.render("coin", tmp_path / "x.png")

    def test_success_returns_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A real output file is accepted and returned."""
        out = tmp_path / "coin.png"

        def _write(*_args: object, **_kwargs: object) -> _Result:
            out.write_bytes(b"png")
            return _Result()

        monkeypatch.setattr(blender.shutil, "which", lambda _: "/bin/true")
        monkeypatch.setattr(blender.subprocess, "run", _write)
        assert blender.render("coin", out) == out
