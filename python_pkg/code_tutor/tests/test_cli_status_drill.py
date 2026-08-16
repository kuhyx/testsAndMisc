"""Tests for the code_tutor status and drill commands."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from python_pkg.code_tutor.cli import app

if TYPE_CHECKING:
    from pathlib import Path

runner = CliRunner()


def _make_plan(codebase: Path, fingerprint: str = "abc") -> dict:
    return {
        "codebase_path": str(codebase),
        "created_at": "2026-01-01T00:00:00+00:00",
        "total_items": 2,
        "source_fingerprint": fingerprint,
        "sessions": [
            {
                "id": 1,
                "title": "mod",
                "items": [
                    {
                        "id": "mod.fn",
                        "file": "mod.py",
                        "type": "function",
                        "name": "fn",
                        "start_line": 1,
                        "end_line": 3,
                        "class_name": "",
                        "depends_on": [],
                    }
                ],
            }
        ],
    }


# ---------------------------------------------------------------------------
# status command
# ---------------------------------------------------------------------------


def test_status_no_plan(tmp_path: Path) -> None:
    with patch("python_pkg.code_tutor.cli.load_plan", return_value=None):
        result = runner.invoke(app, ["status", str(tmp_path)])
    assert result.exit_code == 1


def test_status_with_plan(tmp_path: Path) -> None:
    plan = _make_plan(tmp_path)
    progress = {"learned": [], "struggled": [], "skipped": [], "last_session": ""}
    with (
        patch("python_pkg.code_tutor.cli.load_plan", return_value=plan),
        patch("python_pkg.code_tutor.cli._ensure_fresh_plan", return_value=plan),
        patch("python_pkg.code_tutor.cli.load_progress", return_value=progress),
    ):
        result = runner.invoke(app, ["status", str(tmp_path)])
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# drill command
# ---------------------------------------------------------------------------


def test_drill_no_plan_for_file(tmp_path: Path) -> None:
    f = tmp_path / "mod.py"
    f.write_text("def fn(): pass\n", encoding="utf-8")
    with patch("python_pkg.code_tutor.cli._find_codebase_for_file", return_value=None):
        result = runner.invoke(app, ["drill", str(f)])
    assert result.exit_code == 1


def test_drill_plan_disappears(tmp_path: Path) -> None:
    f = tmp_path / "mod.py"
    f.write_text("def fn(): pass\n", encoding="utf-8")
    with (
        patch(
            "python_pkg.code_tutor.cli._find_codebase_for_file", return_value=tmp_path
        ),
        patch("python_pkg.code_tutor.cli.load_plan", return_value=None),
    ):
        result = runner.invoke(app, ["drill", str(f)])
    assert result.exit_code == 1


def test_drill_no_items_in_plan(tmp_path: Path) -> None:
    f = tmp_path / "other.py"
    f.write_text("def fn(): pass\n", encoding="utf-8")
    plan = _make_plan(tmp_path)  # plan has mod.py items, not other.py
    with (
        patch(
            "python_pkg.code_tutor.cli._find_codebase_for_file", return_value=tmp_path
        ),
        patch("python_pkg.code_tutor.cli.load_plan", return_value=plan),
        patch("python_pkg.code_tutor.cli._ensure_fresh_plan", return_value=plan),
    ):
        result = runner.invoke(app, ["drill", str(f)])
    assert result.exit_code == 0


def test_drill_ollama_fails(tmp_path: Path) -> None:
    f = tmp_path / "mod.py"
    f.write_text("def fn(): pass\n", encoding="utf-8")
    plan = _make_plan(tmp_path)
    with (
        patch(
            "python_pkg.code_tutor.cli._find_codebase_for_file", return_value=tmp_path
        ),
        patch("python_pkg.code_tutor.cli.load_plan", return_value=plan),
        patch("python_pkg.code_tutor.cli._ensure_fresh_plan", return_value=plan),
        patch("python_pkg.code_tutor.cli._ensure_ollama_running", return_value=False),
    ):
        result = runner.invoke(app, ["drill", str(f)])
    assert result.exit_code == 1


def test_drill_runs_lesson(tmp_path: Path) -> None:
    from python_pkg.code_tutor._progress import LessonRecord

    f = tmp_path / "mod.py"
    f.write_text("def fn(): pass\n", encoding="utf-8")
    plan = _make_plan(tmp_path)

    record = LessonRecord(
        timestamp="t",
        item_id="mod.fn",
        file="mod.py",
        lines="1-3",
        snippet="code",
        outcome="learned",
        answers={},
        improvement="",
        verdict="PASS",
        attempt=1,
    )
    mock_verifier = MagicMock()
    mock_verifier.run_lesson.return_value = record

    with (
        patch(
            "python_pkg.code_tutor.cli._find_codebase_for_file", return_value=tmp_path
        ),
        patch("python_pkg.code_tutor.cli.load_plan", return_value=plan),
        patch("python_pkg.code_tutor.cli._ensure_fresh_plan", return_value=plan),
        patch("python_pkg.code_tutor.cli._ensure_ollama_running", return_value=True),
        patch("python_pkg.code_tutor.cli.Verifier", return_value=mock_verifier),
        patch("python_pkg.code_tutor.cli.append_session_record"),
    ):
        result = runner.invoke(app, ["drill", str(f)])
    assert result.exit_code == 0
    mock_verifier.run_lesson.assert_called_once()
