"""Tests for the code_tutor CLI commands themselves."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import requests
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
# analyze command
# ---------------------------------------------------------------------------


def test_analyze_not_dir(tmp_path: Path) -> None:
    result = runner.invoke(app, ["analyze", str(tmp_path / "no_such_dir")])
    assert result.exit_code == 1


def test_analyze_no_items(tmp_path: Path) -> None:
    with patch("python_pkg.code_tutor.cli.extract_items", return_value=[]):
        result = runner.invoke(app, ["analyze", str(tmp_path)])
    assert result.exit_code == 0


def test_analyze_with_items(tmp_path: Path) -> None:
    mock_items = [MagicMock()]
    mock_plan = _make_plan(tmp_path)
    with (
        patch("python_pkg.code_tutor.cli.extract_items", return_value=mock_items),
        patch("python_pkg.code_tutor.cli.build_plan", return_value=mock_plan),
        patch("python_pkg.code_tutor.cli.save_plan"),
        patch("python_pkg.code_tutor.cli.config_dir", return_value=tmp_path),
    ):
        result = runner.invoke(app, ["analyze", str(tmp_path)])
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# study command
# ---------------------------------------------------------------------------


def test_study_not_dir(tmp_path: Path) -> None:
    result = runner.invoke(app, ["study", str(tmp_path / "no_such_dir")])
    assert result.exit_code == 1


def test_study_no_plan(tmp_path: Path) -> None:
    with patch("python_pkg.code_tutor.cli.load_plan", return_value=None):
        result = runner.invoke(app, ["study", str(tmp_path)])
    assert result.exit_code == 1


def test_study_ollama_fails(tmp_path: Path) -> None:
    plan = _make_plan(tmp_path)
    with (
        patch("python_pkg.code_tutor.cli.load_plan", return_value=plan),
        patch("python_pkg.code_tutor.cli._ensure_fresh_plan", return_value=plan),
        patch("python_pkg.code_tutor.cli._ensure_ollama_running", return_value=False),
    ):
        result = runner.invoke(app, ["study", str(tmp_path)])
    assert result.exit_code == 1


def test_study_connection_error(tmp_path: Path) -> None:
    plan = _make_plan(tmp_path)
    with (
        patch("python_pkg.code_tutor.cli.load_plan", return_value=plan),
        patch("python_pkg.code_tutor.cli._ensure_fresh_plan", return_value=plan),
        patch("python_pkg.code_tutor.cli._ensure_ollama_running", return_value=True),
        patch(
            "python_pkg.code_tutor.cli.run_session",
            side_effect=requests.exceptions.ConnectionError(),
        ),
    ):
        result = runner.invoke(app, ["study", str(tmp_path)])
    assert result.exit_code == 1


def test_study_success(tmp_path: Path) -> None:
    plan = _make_plan(tmp_path)
    with (
        patch("python_pkg.code_tutor.cli.load_plan", return_value=plan),
        patch("python_pkg.code_tutor.cli._ensure_fresh_plan", return_value=plan),
        patch("python_pkg.code_tutor.cli._ensure_ollama_running", return_value=True),
        patch("python_pkg.code_tutor.cli.run_session"),
    ):
        result = runner.invoke(app, ["study", str(tmp_path)])
    assert result.exit_code == 0
