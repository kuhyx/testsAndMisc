"""The soft-optional focus-tracker heartbeat on ``show`` and ``check``."""

from __future__ import annotations

import logging
import sys
import types
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import patch

import pytest
import sql_drills as sd

from python_pkg.sql_drills import __main__ as cli

if TYPE_CHECKING:
    from pathlib import Path


def _fake_tracker(
    monkeypatch: pytest.MonkeyPatch, *, fail: bool = False
) -> list[tuple[Any, ...]]:
    calls: list[tuple[Any, ...]] = []
    module = cast("Any", types.ModuleType("focus_project"))

    def record_activity(*args: str) -> None:
        if fail:
            msg = "tracker down"
            raise OSError(msg)
        calls.append(args)

    module.record_activity = record_activity
    monkeypatch.setitem(sys.modules, "focus_project", module)
    return calls


def test_show_sends_heartbeat(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _fake_tracker(monkeypatch)
    assert cli.main(["show", "01"]) == 0
    assert calls == [("sql_drills", "heartbeat")]


def test_check_sends_heartbeat(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls = _fake_tracker(monkeypatch)
    result = sd.RunResult(
        ok=True, error=None, columns=[], rows=[], expected_rows=[["x"]], match=False
    )
    with patch.object(sd, "run", return_value=result):
        query = tmp_path / "q.sql"
        query.write_text("SELECT 1;")
        assert cli.main(["check", "01", str(query)]) == 1
    assert calls == [("sql_drills", "heartbeat")]


def test_list_sends_no_heartbeat(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _fake_tracker(monkeypatch)
    assert cli.main(["list"]) == 0
    assert calls == []


def test_missing_tracker_changes_nothing(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["show", "01"]) == 0
    assert "CREATE TABLE" in capsys.readouterr().out


def test_failing_tracker_is_logged_not_raised(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _fake_tracker(monkeypatch, fail=True)
    with caplog.at_level(logging.ERROR):
        assert cli.main(["show", "01"]) == 0
    assert "heartbeat" in caplog.text
    assert "CREATE TABLE" in capsys.readouterr().out
