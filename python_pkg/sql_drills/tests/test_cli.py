"""CLI wiring: subcommands, exit codes, output."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from python_pkg.sql_drills import __main__ as cli
from python_pkg.sql_drills import _check, _engine


def test_list_prints_ids_and_titles(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["list"]) == 0
    out = capsys.readouterr().out
    assert "01_" in out
    assert len(out.strip().splitlines()) >= 10


def test_show_prints_task(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["show", "01"]) == 0
    assert "CREATE TABLE" in capsys.readouterr().out


def test_show_unknown_drill_exit_2(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["show", "zzz"]) == 2
    assert "unknown drill" in capsys.readouterr().err


def test_start_and_stop_call_engine(capsys: pytest.CaptureFixture[str]) -> None:
    with patch.object(_engine, "start") as start, patch.object(_engine, "stop") as stop:
        assert cli.main(["start"]) == 0
        assert cli.main(["stop"]) == 0
    start.assert_called_once_with()
    stop.assert_called_once_with()
    assert "ready" in capsys.readouterr().out


def test_engine_error_is_exit_2(capsys: pytest.CaptureFixture[str]) -> None:
    with patch.object(_engine, "start", side_effect=_engine.EngineError("boom")):
        assert cli.main(["start"]) == 2
    assert "boom" in capsys.readouterr().err


@pytest.mark.parametrize(("status", "code"), [("pass", 0), ("fail", 1), ("error", 2)])
def test_check_exit_codes(
    status: str, code: int, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    result = _check.CheckResult(status, "MSG")
    with patch.object(_check, "run_check", return_value=result):
        assert cli.main(["check", "01", str(tmp_path / "q.sql")]) == code
    assert "MSG" in capsys.readouterr().out


def test_check_unknown_drill(tmp_path: Path) -> None:
    assert cli.main(["check", "zzz", str(tmp_path / "q.sql")]) == 2


def test_check_engine_error_exit_2(tmp_path: Path) -> None:
    with patch.object(_check, "run_check", side_effect=_engine.EngineError("x")):
        assert cli.main(["check", "01", str(tmp_path / "q.sql")]) == 2


def test_no_subcommand_is_usage_error() -> None:
    with pytest.raises(SystemExit):
        cli.main([])
