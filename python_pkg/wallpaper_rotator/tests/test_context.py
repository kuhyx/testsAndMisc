"""Tests for the render context built for the running desktop."""

from __future__ import annotations

from pathlib import Path

import pytest

from python_pkg.wallpaper_rotator import _context


def test_live_context_points_at_the_users_dirs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(Path, "home", classmethod(lambda _cls: tmp_path))
    monkeypatch.setattr(_context, "DEFAULT_CACHE", tmp_path / ".cache" / "w")
    ctx = _context.RenderContext.live()
    assert ctx.data_home == tmp_path / ".local" / "share"
    assert ctx.earth_dir == tmp_path / ".cache" / "w" / "earth"
    assert ctx.shutdown_conf == Path("/etc/shutdown-schedule.conf")
    assert ctx.now.tzinfo is not None
