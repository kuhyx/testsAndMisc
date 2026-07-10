"""Tests for python_pkg.code_tutor._progress."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from python_pkg.code_tutor._progress import (
    LessonRecord,
    append_session_record,
    config_dir,
    item_from_data,
    load_plan,
    load_progress,
    save_plan,
    save_progress,
)


def _fake_home(tmp_path: Path) -> Path:
    home = tmp_path / "home"
    home.mkdir()
    return home


# ---------------------------------------------------------------------------
# config_dir
# ---------------------------------------------------------------------------


def test_config_dir_returns_path(tmp_path: Path) -> None:
    with patch(
        "python_pkg.code_tutor._progress.Path.home", return_value=_fake_home(tmp_path)
    ):
        result = config_dir(tmp_path / "codebase")
    assert isinstance(result, Path)
    assert "code_tutor" in str(result)


# ---------------------------------------------------------------------------
# load_plan / save_plan
# ---------------------------------------------------------------------------


def test_load_plan_missing(tmp_path: Path) -> None:
    with patch(
        "python_pkg.code_tutor._progress.Path.home", return_value=_fake_home(tmp_path)
    ):
        result = load_plan(tmp_path / "cb")
    assert result is None


def test_save_and_load_plan(tmp_path: Path) -> None:
    home = _fake_home(tmp_path)
    codebase = tmp_path / "cb"
    plan: dict[str, object] = {
        "codebase_path": str(codebase),
        "created_at": "2026-01-01T00:00:00+00:00",
        "total_items": 0,
        "source_fingerprint": "abc",
        "sessions": [],
    }
    with patch("python_pkg.code_tutor._progress.Path.home", return_value=home):
        save_plan(codebase, plan)
        loaded = load_plan(codebase)
    assert loaded is not None
    assert loaded["total_items"] == 0


# ---------------------------------------------------------------------------
# load_progress / save_progress
# ---------------------------------------------------------------------------


def test_load_progress_missing(tmp_path: Path) -> None:
    with patch(
        "python_pkg.code_tutor._progress.Path.home", return_value=_fake_home(tmp_path)
    ):
        result = load_progress(tmp_path / "cb")
    assert result["learned"] == []
    assert result["struggled"] == []
    assert result["skipped"] == []
    assert result["last_session"] == ""


def test_save_and_load_progress(tmp_path: Path) -> None:
    home = _fake_home(tmp_path)
    codebase = tmp_path / "cb"
    progress = {
        "learned": ["a.fn"],
        "struggled": [],
        "skipped": ["b.fn"],
        "last_session": "2026-01-01T00:00:00+00:00",
    }
    with patch("python_pkg.code_tutor._progress.Path.home", return_value=home):
        save_progress(codebase, progress)
        loaded = load_progress(codebase)
    assert loaded["learned"] == ["a.fn"]
    assert loaded["skipped"] == ["b.fn"]


# ---------------------------------------------------------------------------
# append_session_record
# ---------------------------------------------------------------------------


def test_append_session_record(tmp_path: Path) -> None:
    home = _fake_home(tmp_path)
    codebase = tmp_path / "cb"
    record = LessonRecord(
        timestamp="2026-01-01T00:00:00+00:00",
        item_id="mod.fn",
        file="mod.py",
        lines="1-10",
        snippet="def fn(): pass",
        outcome="learned",
        answers={"Purpose": "does stuff"},
        improvement="",
        verdict="PASS",
        attempt=1,
    )
    with patch("python_pkg.code_tutor._progress.Path.home", return_value=home):
        append_session_record(codebase, record)
        cfg = config_dir(codebase)
        sessions_dir = cfg / "sessions"
    assert sessions_dir.exists()
    jsonl_files = list(sessions_dir.glob("*.jsonl"))
    assert len(jsonl_files) == 1
    content = jsonl_files[0].read_text(encoding="utf-8")
    assert "mod.fn" in content


# ---------------------------------------------------------------------------
# item_from_data
# ---------------------------------------------------------------------------


def test_item_from_data() -> None:
    data = {
        "id": "mod.fn",
        "file": "mod.py",
        "type": "function",
        "name": "fn",
        "start_line": 1,
        "end_line": 5,
        "class_name": "",
        "depends_on": [],
    }
    item = item_from_data(data)
    assert item.id == "mod.fn"
    assert item.name == "fn"
    assert item.start_line == 1


# ---------------------------------------------------------------------------
# LessonRecord default challenge_result
# ---------------------------------------------------------------------------


def test_lesson_record_defaults() -> None:
    record = LessonRecord(
        timestamp="t",
        item_id="i",
        file="f.py",
        lines="1-2",
        snippet="code",
        outcome="learned",
        answers={},
        improvement="",
        verdict="PASS",
        attempt=1,
    )
    assert record.challenge_result == ""
