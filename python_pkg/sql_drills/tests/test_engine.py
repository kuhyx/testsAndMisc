"""Docker plumbing with ``subprocess.run`` mocked: no daemon needed."""

from __future__ import annotations

from contextlib import AbstractContextManager
import shutil
import subprocess
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from python_pkg.sql_drills import _engine

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture(autouse=True)
def _fake_docker_on_path() -> Iterator[None]:
    with patch.object(shutil, "which", return_value="docker"):
        yield


def _cp(rc: int = 0, out: str = "", err: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess([], rc, out, err)


def _run(
    *results: subprocess.CompletedProcess[str],
) -> AbstractContextManager[MagicMock | AsyncMock]:
    return patch.object(subprocess, "run", side_effect=list(results))


def test_docker_missing_binary_is_engine_error() -> None:
    with (
        patch.object(shutil, "which", return_value=None),
        pytest.raises(_engine.EngineError, match="docker"),
    ):
        _engine.container_state()


def test_container_state_running() -> None:
    with _run(_cp(0, "running\n")):
        assert _engine.container_state() == "running"


def test_container_state_missing_on_inspect_failure() -> None:
    with _run(_cp(1, "", "No such object")):
        assert _engine.container_state() == "missing"


def test_is_ready_follows_ping_exit_code() -> None:
    with _run(_cp(0)):
        assert _engine.is_ready()
    with _run(_cp(1)):
        assert not _engine.is_ready()


def test_start_creates_container_when_missing_then_waits() -> None:
    with _run(_cp(1), _cp(0, "id"), _cp(1), _cp(0)) as run:
        _engine.start(timeout=5, sleep=lambda _s: None)
    run_args = run.call_args_list[1].args[0]
    assert run_args[:3] == ["docker", "run", "-d"]
    assert "--tmpfs" in run_args
    assert _engine.IMAGE in run_args
    assert "--name" in run_args
    assert _engine.CONTAINER in run_args


def test_start_resumes_exited_container() -> None:
    with _run(_cp(0, "exited\n"), _cp(0), _cp(0)) as run:
        _engine.start(timeout=5, sleep=lambda _s: None)
    assert run.call_args_list[1].args[0][:2] == ["docker", "start"]


def test_start_when_already_running_only_waits() -> None:
    with _run(_cp(0, "running\n"), _cp(0)) as run:
        _engine.start(timeout=5, sleep=lambda _s: None)
    assert run.call_count == 2


def test_start_run_failure_is_reported() -> None:
    with (
        _run(_cp(1), _cp(125, "", "pull access denied")),
        pytest.raises(_engine.EngineError, match="pull access denied"),
    ):
        _engine.start(timeout=5, sleep=lambda _s: None)


def test_start_times_out_with_rerun_hint() -> None:
    ticks = iter([0.0, 1.0, 2.0, 99.0, 100.0])
    results = [_cp(0, "running\n")] + [_cp(1)] * 10
    with _run(*results), pytest.raises(_engine.EngineError, match="rerun"):
        _engine.start(timeout=10, sleep=lambda _s: None, clock=lambda: next(ticks))


def test_stop_removes_container() -> None:
    with _run(_cp(0)) as run:
        _engine.stop()
    assert run.call_args.args[0] == ["docker", "rm", "-f", _engine.CONTAINER]


def test_run_sql_passes_stdin_and_database() -> None:
    with _run(_cp(0, "1\n", "")) as run:
        res = _engine.run_sql("SELECT 1;", database="d1")
    argv = run.call_args.args[0]
    assert argv[:3] == ["docker", "exec", "-i"]
    assert "-B" in argv
    assert "-N" in argv
    assert argv[-1] == "d1"
    assert run.call_args.kwargs["input"] == "SELECT 1;"
    assert res.returncode == 0
    assert res.stdout == "1\n"


def test_run_sql_without_database() -> None:
    with _run(_cp(0)) as run:
        _engine.run_sql("SELECT 1;")
    assert run.call_args.args[0][-1] == "-N"


def test_run_sql_timeout_becomes_engine_error() -> None:
    boom = subprocess.TimeoutExpired(cmd="docker", timeout=1)
    with (
        patch.object(subprocess, "run", side_effect=boom),
        pytest.raises(_engine.EngineError, match="timed out"),
    ):
        _engine.run_sql("SELECT SLEEP(99);", timeout=1)


def test_run_sql_missing_docker_is_not_relabelled() -> None:
    with (
        patch.object(shutil, "which", return_value=None),
        pytest.raises(_engine.EngineError, match="docker binary"),
    ):
        _engine.run_sql("SELECT 1;")
