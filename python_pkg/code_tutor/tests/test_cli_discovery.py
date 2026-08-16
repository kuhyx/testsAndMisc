"""Tests for locating a codebase from a single file."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import patch

from typer.testing import CliRunner

from python_pkg.code_tutor._cli_checks import (
    _check_plan_file,
    _find_codebase_for_file,
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
