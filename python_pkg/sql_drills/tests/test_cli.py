"""CLI wiring over the shared package: subcommands, exit codes, output."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
import sql_drills as sd

from python_pkg.sql_drills import __main__ as cli


def _result(
    *,
    match: bool,
    ok: bool = True,
    error: str | None = None,
    diff: list[sd.CellDiff] | None = None,
) -> sd.RunResult:
    return sd.RunResult(
        ok=ok,
        error=error,
        columns=[],
        rows=[["a"]],
        expected_rows=[["b"]],
        match=match,
        cell_diff=diff or [],
    )


def _sql(tmp_path: Path) -> str:
    query = tmp_path / "q.sql"
    query.write_text("SELECT 1;")
    return str(query)


def test_list_prints_ids_and_titles(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["list"]) == 0
    out = capsys.readouterr().out
    assert "01_" in out
    assert len(out.strip().splitlines()) >= 10


def test_show_prints_task_and_expected_sample(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["show", "01"]) == 0
    out = capsys.readouterr().out
    assert "CREATE TABLE" in out
    assert "## Expected output (sample)" in out


def test_show_predict_drill_prints_the_query(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["show", "t03"]) == 0
    out = capsys.readouterr().out
    assert "## Query to predict" in out
    assert "LEFT JOIN" in out


def test_show_unknown_drill_exit_2(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["show", "zzz"]) == 2
    assert "unknown drill" in capsys.readouterr().err


def test_start_and_stop_call_engine(capsys: pytest.CaptureFixture[str]) -> None:
    with (
        patch.object(sd, "ensure_running") as start,
        patch.object(sd, "stop") as stop,
    ):
        assert cli.main(["start"]) == 0
        assert cli.main(["stop"]) == 0
    start.assert_called_once_with()
    stop.assert_called_once_with()
    assert "ready" in capsys.readouterr().out


def test_engine_error_is_exit_2(capsys: pytest.CaptureFixture[str]) -> None:
    with patch.object(sd, "ensure_running", side_effect=sd.EngineError("boom")):
        assert cli.main(["start"]) == 2
    assert "boom" in capsys.readouterr().err


def test_check_pass_is_exit_0(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    with patch.object(sd, "run", return_value=_result(match=True)):
        assert cli.main(["check", "01", _sql(tmp_path)]) == 0
    assert "PASS 01" in capsys.readouterr().out


def test_check_fail_prints_cell_diff_exit_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    res = _result(match=False, diff=[(0, 1, "x", "y")])
    with patch.object(sd, "run", return_value=res):
        assert cli.main(["check", "01", _sql(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert "FAIL 01" in out
    assert "line 1 cell 2: expected 'x', actual 'y'" in out


def test_check_sql_error_is_exit_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    res = _result(match=False, ok=False, error="ERROR 1064")
    with patch.object(sd, "run", return_value=res):
        assert cli.main(["check", "01", _sql(tmp_path)]) == 2
    assert "ERROR 1064" in capsys.readouterr().out


def test_check_missing_file_is_exit_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert cli.main(["check", "01", str(tmp_path / "nope.sql")]) == 2
    assert "not found" in capsys.readouterr().out


def test_check_unknown_drill(tmp_path: Path) -> None:
    assert cli.main(["check", "zzz", _sql(tmp_path)]) == 2


def test_check_engine_error_exit_2(tmp_path: Path) -> None:
    with patch.object(sd, "run", side_effect=sd.EngineError("x")):
        assert cli.main(["check", "01", _sql(tmp_path)]) == 2


def test_no_subcommand_is_usage_error() -> None:
    with pytest.raises(SystemExit):
        cli.main([])
