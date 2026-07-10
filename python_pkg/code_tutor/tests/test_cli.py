"""Tests for python_pkg.code_tutor.cli."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import requests
from typer.testing import CliRunner

from python_pkg.code_tutor.cli import (
    _check_plan_file,
    _ensure_fresh_plan,
    _ensure_ollama_running,
    _find_codebase_for_file,
    app,
)

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
# _ensure_ollama_running
# ---------------------------------------------------------------------------


def test_ensure_ollama_running_already_up() -> None:
    mock_console = MagicMock()
    mock_resp = MagicMock()
    with patch("python_pkg.code_tutor.cli.requests.get", return_value=mock_resp):
        result = _ensure_ollama_running(mock_console)
    assert result is True


def test_ensure_ollama_running_systemctl_fails() -> None:
    import subprocess

    mock_console = MagicMock()
    with (
        patch(
            "python_pkg.code_tutor.cli.requests.get",
            side_effect=requests.exceptions.ConnectionError(),
        ),
        patch(
            "python_pkg.code_tutor.cli.subprocess.run",
            side_effect=subprocess.CalledProcessError(1, "systemctl", stderr=b"failed"),
        ),
    ):
        result = _ensure_ollama_running(mock_console)
    assert result is False


def test_ensure_ollama_running_starts_then_up() -> None:
    mock_console = MagicMock()
    mock_subprocess = MagicMock()
    request_calls = [0]

    def fake_get(*args: object, **kwargs: object) -> MagicMock:
        request_calls[0] += 1
        if request_calls[0] == 1:
            raise requests.exceptions.ConnectionError
        return MagicMock()

    with (
        patch("python_pkg.code_tutor.cli.requests.get", side_effect=fake_get),
        patch("python_pkg.code_tutor.cli.subprocess.run", return_value=mock_subprocess),
        patch("python_pkg.code_tutor.cli.time.sleep"),
    ):
        result = _ensure_ollama_running(mock_console)
    assert result is True


def test_ensure_ollama_running_times_out() -> None:
    mock_console = MagicMock()
    mock_subprocess = MagicMock()

    time_values = iter(
        [0, 0, 100]
    )  # deadline=30, first while check→0 (enter), next→100 (exit)

    def fake_get(*args: object, **kwargs: object) -> MagicMock:
        raise requests.exceptions.ConnectionError

    with (
        patch("python_pkg.code_tutor.cli.requests.get", side_effect=fake_get),
        patch("python_pkg.code_tutor.cli.subprocess.run", return_value=mock_subprocess),
        patch(
            "python_pkg.code_tutor.cli.time.monotonic",
            side_effect=time_values,
        ),
        patch("python_pkg.code_tutor.cli.time.sleep"),
    ):
        result = _ensure_ollama_running(mock_console)
    assert result is False


# ---------------------------------------------------------------------------
# _ensure_fresh_plan
# ---------------------------------------------------------------------------


def test_ensure_fresh_plan_no_fingerprint(tmp_path: Path) -> None:
    plan = {
        "codebase_path": str(tmp_path),
        "created_at": "t",
        "total_items": 0,
        "source_fingerprint": "",
        "sessions": [],
    }
    mock_console = MagicMock()
    result = _ensure_fresh_plan(tmp_path, plan, mock_console)
    assert result is plan


def test_ensure_fresh_plan_up_to_date(tmp_path: Path) -> None:
    plan = _make_plan(tmp_path, fingerprint="same")
    mock_console = MagicMock()
    with patch("python_pkg.code_tutor.cli.codebase_fingerprint", return_value="same"):
        result = _ensure_fresh_plan(tmp_path, plan, mock_console)
    assert result is plan


def test_ensure_fresh_plan_stale_no_items(tmp_path: Path) -> None:
    plan = _make_plan(tmp_path, fingerprint="old")
    mock_console = MagicMock()
    with (
        patch("python_pkg.code_tutor.cli.codebase_fingerprint", return_value="new"),
        patch("python_pkg.code_tutor.cli.extract_items", return_value=[]),
    ):
        result = _ensure_fresh_plan(tmp_path, plan, mock_console)
    assert result is plan


def test_ensure_fresh_plan_stale_rebuilds(tmp_path: Path) -> None:
    plan = _make_plan(tmp_path, fingerprint="old")
    new_plan = _make_plan(tmp_path, fingerprint="new")
    mock_console = MagicMock()
    mock_items = [MagicMock()]

    with (
        patch("python_pkg.code_tutor.cli.codebase_fingerprint", return_value="new"),
        patch("python_pkg.code_tutor.cli.extract_items", return_value=mock_items),
        patch("python_pkg.code_tutor.cli.build_plan", return_value=new_plan),
        patch("python_pkg.code_tutor.cli.save_plan"),
    ):
        result = _ensure_fresh_plan(tmp_path, plan, mock_console)
    assert result["source_fingerprint"] == "new"


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


# ---------------------------------------------------------------------------
# _find_codebase_for_file
# ---------------------------------------------------------------------------


def test_find_codebase_for_file_no_config_dir(tmp_path: Path) -> None:
    with patch(
        "python_pkg.code_tutor.cli.Path.home",
        return_value=tmp_path,
    ):
        result = _find_codebase_for_file(tmp_path / "mod.py")
    assert result is None


def test_find_codebase_for_file_found(tmp_path: Path) -> None:
    home = tmp_path / "home"
    config_root = home / ".config" / "code_tutor" / "hash"
    config_root.mkdir(parents=True)
    codebase = tmp_path / "codebase"
    codebase.mkdir()
    f = codebase / "mod.py"
    f.write_text("def fn(): pass\n", encoding="utf-8")

    plan_data = {
        "codebase_path": str(codebase),
        "sessions": [],
    }
    (config_root / "plan.json").write_text(json.dumps(plan_data), encoding="utf-8")

    with patch("python_pkg.code_tutor.cli.Path.home", return_value=home):
        result = _find_codebase_for_file(f)

    assert result == codebase


def test_find_codebase_for_file_not_found(tmp_path: Path) -> None:
    home = tmp_path / "home"
    config_root = home / ".config" / "code_tutor" / "hash"
    config_root.mkdir(parents=True)

    other_codebase = tmp_path / "other"
    other_codebase.mkdir()
    plan_data = {"codebase_path": str(other_codebase), "sessions": []}
    (config_root / "plan.json").write_text(json.dumps(plan_data), encoding="utf-8")

    target = tmp_path / "unrelated" / "mod.py"

    with patch("python_pkg.code_tutor.cli.Path.home", return_value=home):
        result = _find_codebase_for_file(target)

    assert result is None


# ---------------------------------------------------------------------------
# _check_plan_file
# ---------------------------------------------------------------------------


def test_check_plan_file_found(tmp_path: Path) -> None:
    codebase = tmp_path / "cb"
    codebase.mkdir()
    f = codebase / "mod.py"
    plan_file = tmp_path / "plan.json"
    plan_file.write_text(json.dumps({"codebase_path": str(codebase)}), encoding="utf-8")
    result = _check_plan_file(plan_file, f)
    assert result == codebase


def test_check_plan_file_value_error(tmp_path: Path) -> None:
    codebase = tmp_path / "cb"
    codebase.mkdir()
    other_file = tmp_path / "other" / "mod.py"
    plan_file = tmp_path / "plan.json"
    plan_file.write_text(json.dumps({"codebase_path": str(codebase)}), encoding="utf-8")
    # other_file is not relative to codebase → ValueError
    result = _check_plan_file(plan_file, other_file)
    assert result is None


def test_check_plan_file_oserror(tmp_path: Path) -> None:
    plan_file = tmp_path / "missing_plan.json"
    result = _check_plan_file(plan_file, tmp_path / "mod.py")
    assert result is None


def test_check_plan_file_json_error(tmp_path: Path) -> None:
    plan_file = tmp_path / "plan.json"
    plan_file.write_text("not valid json {{{", encoding="utf-8")
    result = _check_plan_file(plan_file, tmp_path / "mod.py")
    assert result is None
