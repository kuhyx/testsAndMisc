"""Tests for the standing-cost checkup report."""

from __future__ import annotations

import pytest

from python_pkg.token_audit import checkup, surfaces, unused


@pytest.fixture(autouse=True)
def stub_sources(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace disk scans with fixed rows so the render is deterministic."""
    monkeypatch.setattr(
        surfaces,
        "collect",
        lambda: [
            surfaces.Surface("rules/", "always-on", 4000),
            surfaces.Surface("global MCP", "13 active", 0, measurable=True),
        ],
    )
    monkeypatch.setattr(
        unused,
        "mcp_usage",
        lambda: [unused.Usage("reaper", 0, 0), unused.Usage("ck3", 0, 9)],
    )
    monkeypatch.setattr(unused, "skill_usage", lambda: [unused.Usage("grilling", 0, 0)])


def test_report_lists_every_surface() -> None:
    """A surface present in the enumeration reaches the report."""
    text = checkup.build(44311, 1230346533)
    assert "rules/" in text
    assert "global MCP" in text


def test_disk_sized_surface_shows_weighted_share() -> None:
    """Shares are weighted, not raw — the unit error an audit made."""
    text = checkup.build(44311, 1230346533)
    assert "| 1,000 | 0.36% |" in text


def test_unmeasurable_surface_is_labelled() -> None:
    """A surface that needs an A/B says so rather than reporting zero bytes."""
    assert "A/B only" in checkup.build(1000, 1000000)


def test_only_both_window_zero_is_parked() -> None:
    """ck3 (unused 7d, used 30d) must not be recommended for parking."""
    text = checkup.build(44311, 1230346533)
    assert "| reaper | 0 | 0 | **park** |" in text
    assert "| ck3 | 0 | 9 | keep |" in text


def test_skills_section_present() -> None:
    """Skills are audited alongside MCP servers."""
    assert "## Skills" in checkup.build(1000, 1000000)


def test_main_defaults_and_args(capsys: pytest.CaptureFixture[str]) -> None:
    """The CLI accepts turns and total, and defaults when omitted."""
    assert checkup.main([]) == 0
    assert "Standing-cost checkup" in capsys.readouterr().out
    assert checkup.main(["100", "1000000"]) == 0
    assert "100 turns" in capsys.readouterr().out
