"""Tests for python_pkg.code_tutor.cli."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import requests
from typer.testing import CliRunner

from python_pkg.code_tutor._cli_checks import (
    _ensure_fresh_plan,
    _ensure_ollama_running,
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
    with patch(
        "python_pkg.code_tutor._cli_checks.requests.get", return_value=mock_resp
    ):
        result = _ensure_ollama_running(mock_console)
    assert result is True


def test_ensure_ollama_running_no_systemctl() -> None:
    """A machine without systemctl should say so, not raise."""
    mock_console = MagicMock()
    with (
        patch(
            "python_pkg.code_tutor._cli_checks.requests.get",
            side_effect=requests.exceptions.ConnectionError(),
        ),
        patch("python_pkg.code_tutor._cli_checks.shutil.which", return_value=None),
    ):
        result = _ensure_ollama_running(mock_console)
    assert result is False


def test_ensure_ollama_running_systemctl_fails() -> None:
    import subprocess

    mock_console = MagicMock()
    with (
        patch(
            "python_pkg.code_tutor._cli_checks.requests.get",
            side_effect=requests.exceptions.ConnectionError(),
        ),
        patch(
            "python_pkg.code_tutor._cli_checks.subprocess.run",
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
        patch("python_pkg.code_tutor._cli_checks.requests.get", side_effect=fake_get),
        patch(
            "python_pkg.code_tutor._cli_checks.subprocess.run",
            return_value=mock_subprocess,
        ),
        patch("python_pkg.code_tutor._cli_checks.time.sleep"),
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
        patch("python_pkg.code_tutor._cli_checks.requests.get", side_effect=fake_get),
        patch(
            "python_pkg.code_tutor._cli_checks.subprocess.run",
            return_value=mock_subprocess,
        ),
        patch(
            "python_pkg.code_tutor._cli_checks.time.monotonic",
            side_effect=time_values,
        ),
        patch("python_pkg.code_tutor._cli_checks.time.sleep"),
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
    with patch(
        "python_pkg.code_tutor._cli_checks.codebase_fingerprint", return_value="same"
    ):
        result = _ensure_fresh_plan(tmp_path, plan, mock_console)
    assert result is plan


def test_ensure_fresh_plan_stale_no_items(tmp_path: Path) -> None:
    plan = _make_plan(tmp_path, fingerprint="old")
    mock_console = MagicMock()
    with (
        patch(
            "python_pkg.code_tutor._cli_checks.codebase_fingerprint", return_value="new"
        ),
        patch("python_pkg.code_tutor._cli_checks.extract_items", return_value=[]),
    ):
        result = _ensure_fresh_plan(tmp_path, plan, mock_console)
    assert result is plan


def test_ensure_fresh_plan_stale_rebuilds(tmp_path: Path) -> None:
    plan = _make_plan(tmp_path, fingerprint="old")
    new_plan = _make_plan(tmp_path, fingerprint="new")
    mock_console = MagicMock()
    mock_items = [MagicMock()]

    with (
        patch(
            "python_pkg.code_tutor._cli_checks.codebase_fingerprint", return_value="new"
        ),
        patch(
            "python_pkg.code_tutor._cli_checks.extract_items", return_value=mock_items
        ),
        patch("python_pkg.code_tutor._cli_checks.build_plan", return_value=new_plan),
        patch("python_pkg.code_tutor._cli_checks.save_plan"),
    ):
        result = _ensure_fresh_plan(tmp_path, plan, mock_console)
    assert result["source_fingerprint"] == "new"
