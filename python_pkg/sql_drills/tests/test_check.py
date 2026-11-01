"""``run_check`` orchestration with the engine mocked."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from python_pkg.sql_drills import _check, _drills, _engine
from python_pkg.sql_drills._engine import SqlResult


def _drill(tmp_path: Path, expected: str = "a 1\n") -> _drills.Drill:
    (tmp_path / "DOCS-task.md").write_text("# T\n")
    (tmp_path / "schema.sql").write_text("CREATE TABLE t (a INT);")
    (tmp_path / "expected.txt").write_text(expected)
    return _drills.Drill(
        "09_x",
        tmp_path / "DOCS-task.md",
        tmp_path / "schema.sql",
        tmp_path / "expected.txt",
    )


def _query(tmp_path: Path) -> Path:
    q = tmp_path / "q.sql"
    q.write_text("SELECT 'a', 1;")
    return q


def _patch_engine(*results: SqlResult, ready: bool = True) -> tuple[Any, Any]:
    return (
        patch.object(_engine, "is_ready", return_value=ready),
        patch.object(_engine, "run_sql", side_effect=list(results)),
    )


OK = SqlResult(0, "", "")


def test_pass(tmp_path: Path) -> None:
    ready, run = _patch_engine(OK, OK, SqlResult(0, "a\t1\n", ""))
    with ready, run as run_sql:
        res = _check.run_check(_drill(tmp_path), _query(tmp_path))
    assert res.status == "pass"
    assert run_sql.call_args_list[0].args[0].startswith("DROP DATABASE IF EXISTS")
    assert run_sql.call_args_list[2].kwargs["database"] == "drill_09_x"


def test_mismatch_includes_diff(tmp_path: Path) -> None:
    ready, run = _patch_engine(OK, OK, SqlResult(0, "a\t2\n", ""))
    with ready, run:
        res = _check.run_check(_drill(tmp_path), _query(tmp_path))
    assert res.status == "fail"
    assert "expected: a 1" in res.message
    assert "actual  : a 2" in res.message


def test_sql_error_reports_stderr(tmp_path: Path) -> None:
    ready, run = _patch_engine(OK, OK, SqlResult(1, "", "ERROR 1064: syntax"))
    with ready, run:
        res = _check.run_check(_drill(tmp_path), _query(tmp_path))
    assert res.status == "error"
    assert "ERROR 1064" in res.message


def test_not_ready_tells_user_to_start(tmp_path: Path) -> None:
    ready, run = _patch_engine(ready=False)
    with ready, run:
        res = _check.run_check(_drill(tmp_path), _query(tmp_path))
    assert res.status == "error"
    assert "start" in res.message


def test_schema_failure_is_error(tmp_path: Path) -> None:
    ready, run = _patch_engine(OK, SqlResult(1, "", "bad schema"))
    with ready, run:
        res = _check.run_check(_drill(tmp_path), _query(tmp_path))
    assert res.status == "error"
    assert "bad schema" in res.message


def test_reset_failure_is_error(tmp_path: Path) -> None:
    ready, run = _patch_engine(SqlResult(1, "", "no perms"))
    with ready, run:
        res = _check.run_check(_drill(tmp_path), _query(tmp_path))
    assert res.status == "error"


def test_missing_query_file(tmp_path: Path) -> None:
    ready, run = _patch_engine()
    with ready, run:
        res = _check.run_check(_drill(tmp_path), tmp_path / "nope.sql")
    assert res.status == "error"
    assert "nope.sql" in res.message


def test_engine_error_propagates_to_cli(tmp_path: Path) -> None:
    with (
        patch.object(_engine, "is_ready", side_effect=_engine.EngineError("no docker")),
        pytest.raises(_engine.EngineError),
    ):
        _check.run_check(_drill(tmp_path), _query(tmp_path))
