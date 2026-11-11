"""Tests for the ``python3 -m python_pkg.wallpaper_rotator`` entry point."""

from __future__ import annotations

import logging
import runpy

import pytest

from python_pkg.wallpaper_rotator import _tick


def _run_main(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    outcome: object,
) -> list[str]:
    monkeypatch.setattr(_tick, "tick", lambda: outcome)
    with caplog.at_level(logging.INFO):
        runpy.run_module("python_pkg.wallpaper_rotator", run_name="__main__")
    return caplog.messages


def test_main_reports_a_repaint(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    assert "painted" in _run_main(monkeypatch, caplog, outcome=1)


def test_main_reports_an_unchanged_background(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    assert "unchanged" in _run_main(monkeypatch, caplog, outcome=0)
