"""Tests for python_pkg.code_tutor._session."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from python_pkg.code_tutor._progress import LessonRecord
from python_pkg.code_tutor._session import _items_from_plan, _show_summary, run_session

if TYPE_CHECKING:
    from pathlib import Path


def _make_item_data(name: str = "fn", file: str = "mod.py") -> dict:
    return {
        "id": f"{file}.{name}",
        "file": file,
        "type": "function",
        "name": name,
        "start_line": 1,
        "end_line": 5,
        "class_name": "",
        "depends_on": [],
    }


def _make_plan(items: list[dict]) -> dict:
    return {
        "codebase_path": "/cb",
        "created_at": "2026-01-01T00:00:00+00:00",
        "total_items": len(items),
        "source_fingerprint": "abc",
        "sessions": [{"id": 1, "title": "mod", "items": items}],
    }


def _make_record(item_id: str, outcome: str) -> LessonRecord:
    return LessonRecord(
        timestamp="2026-01-01T00:00:00+00:00",
        item_id=item_id,
        file="mod.py",
        lines="1-5",
        snippet="code",
        outcome=outcome,
        answers={},
        improvement="",
        verdict="PASS" if outcome == "learned" else "FAIL",
        attempt=1,
    )


# ---------------------------------------------------------------------------
# _items_from_plan
# ---------------------------------------------------------------------------


def test_items_from_plan_basic() -> None:
    plan = _make_plan([_make_item_data("fn")])
    items = _items_from_plan(plan)
    assert len(items) == 1
    assert items[0].name == "fn"


def test_items_from_plan_multiple_sessions() -> None:
    plan = {
        "codebase_path": "/cb",
        "created_at": "t",
        "total_items": 2,
        "source_fingerprint": "x",
        "sessions": [
            {"id": 1, "title": "a", "items": [_make_item_data("fn1")]},
            {"id": 2, "title": "b", "items": [_make_item_data("fn2")]},
        ],
    }
    items = _items_from_plan(plan)
    assert len(items) == 2


# ---------------------------------------------------------------------------
# _show_summary
# ---------------------------------------------------------------------------


def test_show_summary_renders_table() -> None:
    mock_console = MagicMock()
    _show_summary(
        {"learned": ["a", "b"], "struggled": ["c"], "skipped": []},
        mock_console,
    )
    mock_console.print.assert_called_once()


def test_show_summary_empty() -> None:
    mock_console = MagicMock()
    _show_summary({}, mock_console)
    mock_console.print.assert_called_once()


# ---------------------------------------------------------------------------
# run_session
# ---------------------------------------------------------------------------


def test_run_session_no_plan(tmp_path: Path) -> None:
    mock_backend = MagicMock()
    mock_console = MagicMock()

    with patch("python_pkg.code_tutor._session.load_plan", return_value=None):
        run_session(tmp_path, mock_backend, console=mock_console)

    mock_console.print.assert_called()


def test_run_session_all_done(tmp_path: Path) -> None:
    plan = _make_plan([_make_item_data("fn")])
    progress = {
        "learned": ["mod.py.fn"],
        "struggled": [],
        "skipped": [],
        "last_session": "",
    }
    mock_backend = MagicMock()
    mock_console = MagicMock()

    with (
        patch("python_pkg.code_tutor._session.load_plan", return_value=plan),
        patch("python_pkg.code_tutor._session.load_progress", return_value=progress),
    ):
        run_session(tmp_path, mock_backend, console=mock_console)

    mock_console.print.assert_called()


def test_run_session_learned(tmp_path: Path) -> None:
    item_data = _make_item_data("fn")
    plan = _make_plan([item_data])
    progress = {"learned": [], "struggled": [], "skipped": [], "last_session": ""}
    record = _make_record("mod.py.fn", "learned")

    mock_backend = MagicMock()
    mock_console = MagicMock()
    mock_verifier = MagicMock()
    mock_verifier.run_lesson.return_value = record

    with (
        patch("python_pkg.code_tutor._session.load_plan", return_value=plan),
        patch("python_pkg.code_tutor._session.load_progress", return_value=progress),
        patch("python_pkg.code_tutor._session.Verifier", return_value=mock_verifier),
        patch("python_pkg.code_tutor._session.append_session_record"),
        patch("python_pkg.code_tutor._session.save_progress"),
    ):
        run_session(tmp_path, mock_backend, console=mock_console)

    assert "mod.py.fn" in progress["learned"]


def test_run_session_struggled(tmp_path: Path) -> None:
    item_data = _make_item_data("fn")
    plan = _make_plan([item_data])
    progress = {"learned": [], "struggled": [], "skipped": [], "last_session": ""}
    record = _make_record("mod.py.fn", "struggled")

    mock_backend = MagicMock()
    mock_console = MagicMock()
    mock_verifier = MagicMock()
    mock_verifier.run_lesson.return_value = record

    with (
        patch("python_pkg.code_tutor._session.load_plan", return_value=plan),
        patch("python_pkg.code_tutor._session.load_progress", return_value=progress),
        patch("python_pkg.code_tutor._session.Verifier", return_value=mock_verifier),
        patch("python_pkg.code_tutor._session.append_session_record"),
        patch("python_pkg.code_tutor._session.save_progress"),
    ):
        run_session(tmp_path, mock_backend, console=mock_console)

    assert "mod.py.fn" in progress["struggled"]


def test_run_session_skipped(tmp_path: Path) -> None:
    item_data = _make_item_data("fn")
    plan = _make_plan([item_data])
    progress = {"learned": [], "struggled": [], "skipped": [], "last_session": ""}
    record = _make_record("mod.py.fn", "skipped")

    mock_backend = MagicMock()
    mock_console = MagicMock()
    mock_verifier = MagicMock()
    mock_verifier.run_lesson.return_value = record

    with (
        patch("python_pkg.code_tutor._session.load_plan", return_value=plan),
        patch("python_pkg.code_tutor._session.load_progress", return_value=progress),
        patch("python_pkg.code_tutor._session.Verifier", return_value=mock_verifier),
        patch("python_pkg.code_tutor._session.append_session_record"),
        patch("python_pkg.code_tutor._session.save_progress"),
    ):
        run_session(tmp_path, mock_backend, console=mock_console)

    assert "mod.py.fn" in progress["skipped"]
