from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from python_pkg.token_audit import attribute, report
from python_pkg.token_audit.model import Session, ToolCall, Turn

if TYPE_CHECKING:
    from pathlib import Path


def _turn(
    out: int = 1,
    read: int = 0,
    create: int = 0,
    context: int = 0,
    *,
    sidechain: bool = False,
) -> Turn:
    return Turn(
        usage={
            "output_tokens": out,
            "cache_read_input_tokens": read,
            "cache_creation_input_tokens": create,
        },
        context=context,
        model="claude-opus-5",
        is_sidechain=sidechain,
    )


def _fixture() -> tuple[attribute.Totals, attribute.Axes, report.Window, list[Session]]:
    session = Session(session_id="abcdef123456", path="p", cwd="/home/kuhy/demo")
    session.turns = [_turn(out=10, create=500), _turn(out=5, read=400, context=400)]
    session.tools = [
        ToolCall(name="Read", result_tokens=900, path="/s.png"),
        ToolCall(name="mcp__aseprite__draw_line", result_tokens=3),
        ToolCall(name="Skill", result_tokens=1, skill="finish"),
    ]
    session.image_cost = 90.0
    totals, axes = attribute.build([session])
    window = report.Window(since=0.0, until=86400.0)
    return totals, axes, window, [session]


def test_window_describe_is_readable() -> None:
    assert "UTC" in report.Window(since=0.0, until=86400.0).describe()


def test_snapshot_has_required_keys() -> None:
    totals, axes, window, sessions = _fixture()
    snap = report.snapshot(totals, axes, window, len(sessions))
    for key in (
        "generated",
        "window",
        "weighted_total",
        "raw",
        "image_cost",
        "projects",
    ):
        assert key in snap
    assert snap["sessions"] == 1


def test_render_contains_each_section() -> None:
    totals, axes, window, sessions = _fixture()
    snap = report.snapshot(totals, axes, window, len(sessions))
    text = report.render(totals, axes, window, sessions, snap, None)
    for heading in (
        "# Claude Code token audit",
        "## Totals",
        "## Ranked drivers",
        "## Projects",
        "## MCP servers invoked",
        "## Skills invoked",
        "## Most expensive sessions",
    ):
        assert heading in text
    assert "aseprite" in text
    assert "finish" in text
    assert "abcdef12" in text


def test_render_without_previous_says_so() -> None:
    totals, axes, window, sessions = _fixture()
    snap = report.snapshot(totals, axes, window, len(sessions))
    assert "No previous report" in report.render(
        totals, axes, window, sessions, snap, None
    )


@pytest.mark.parametrize(
    ("before", "expected"),
    [(100, "down"), (1, "up")],
)
def test_delta_direction(before: int, expected: str) -> None:
    assert expected in report._delta_line(
        {"weighted_total": 50}, {"weighted_total": before}
    )


def test_delta_handles_zero_previous() -> None:
    assert "no spend" in report._delta_line(
        {"weighted_total": 5}, {"weighted_total": 0}
    )


def test_empty_axes_render_placeholders() -> None:
    session = Session(session_id="s", path="p", cwd="/x")
    session.turns = [_turn()]
    totals, axes = attribute.build([session])
    window = report.Window(since=0.0, until=1.0)
    snap = report.snapshot(totals, axes, window, 1)
    text = report.render(totals, axes, window, [session], snap, None)
    assert "(none invoked)" in text


def test_pct_guards_zero_denominator() -> None:
    assert report._pct(1.0, 0.0) == "n/a"


def test_write_creates_both_files(tmp_path: Path) -> None:
    totals, axes, window, sessions = _fixture()
    snap = report.snapshot(totals, axes, window, len(sessions))
    text = report.render(totals, axes, window, sessions, snap, None)
    md_path = report.write(text, snap, tmp_path)
    assert md_path.exists()
    assert (tmp_path / report.JSON_NAME).exists()
    assert json.loads((tmp_path / report.JSON_NAME).read_text())["sessions"] == 1


def test_load_previous_roundtrip(tmp_path: Path) -> None:
    assert report.load_previous(tmp_path) is None
    (tmp_path / report.JSON_NAME).write_text('{"weighted_total": 7}', encoding="utf-8")
    assert report.load_previous(tmp_path) == {"weighted_total": 7}


def test_load_previous_tolerates_corrupt_json(tmp_path: Path) -> None:
    (tmp_path / report.JSON_NAME).write_text("{not json", encoding="utf-8")
    assert report.load_previous(tmp_path) is None


def test_load_previous_rejects_non_object(tmp_path: Path) -> None:
    (tmp_path / report.JSON_NAME).write_text("[1,2]", encoding="utf-8")
    assert report.load_previous(tmp_path) is None
