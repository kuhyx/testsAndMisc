"""Reading Endurain's activity start times straight out of postgres.

The load-bearing distinction is None vs []: None means "could not ask" and
must send the caller back to the ledger, while [] is a real answer meaning
this user has no activities. Swapping them would upload a duplicate every
time docker hiccuped, which is the bug the dedupe check exists to prevent.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
import subprocess

import pytest

from python_pkg.endurain_import import db_lookup


def _proc(
    returncode: int = 0, stdout: str = "", stderr: str = ""
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=["docker"], returncode=returncode, stdout=stdout, stderr=stderr
    )


def _db_returning(
    result: subprocess.CompletedProcess[str] | Exception,
    captured: dict[str, object] | None = None,
) -> db_lookup.EndurainDatabase:
    def _runner(argv: Sequence[str], stdin: str) -> subprocess.CompletedProcess[str]:
        if captured is not None:
            captured["argv"] = list(argv)
            captured["stdin"] = stdin
        if isinstance(result, Exception):
            raise result
        return result

    return db_lookup.EndurainDatabase(runner=_runner)


def test_parses_rows_into_utc() -> None:
    db = _db_returning(_proc(stdout="2026-08-22 23:51:05+02\n2026-08-19 19:10:06+02\n"))
    assert db.recent_start_times(1) == [
        datetime(2026, 8, 22, 21, 51, 5, tzinfo=UTC),
        datetime(2026, 8, 19, 17, 10, 6, tzinfo=UTC),
    ]


def test_empty_table_is_an_answer_not_a_failure() -> None:
    """No rows means "nothing stored" -- callers may act on it."""
    assert _db_returning(_proc(stdout="")).recent_start_times(1) == []


def test_nonzero_exit_is_unknown() -> None:
    """A dead container must not read as "no activities exist"."""
    db = _db_returning(_proc(returncode=1, stderr="No such container"))
    assert db.recent_start_times(1) is None


def test_nonzero_exit_without_stderr_is_unknown() -> None:
    """Covers the empty-stderr branch of the failure message."""
    assert _db_returning(_proc(returncode=2)).recent_start_times(1) is None


def test_subprocess_error_is_unknown() -> None:
    db = _db_returning(subprocess.TimeoutExpired(cmd="docker", timeout=30))
    assert db.recent_start_times(1) is None


def test_os_error_is_unknown() -> None:
    """docker missing from PATH raises OSError, not a SubprocessError."""
    assert _db_returning(OSError("no docker")).recent_start_times(1) is None


def test_unparseable_rows_are_dropped_not_fatal() -> None:
    db = _db_returning(_proc(stdout="not a timestamp\n2026-08-22 23:51:05+02\n\n"))
    assert db.recent_start_times(1) == [datetime(2026, 8, 22, 21, 51, 5, tzinfo=UTC)]


def test_query_is_parameterised_and_user_id_coerced() -> None:
    """user_id reaches psql as a -v binding, never spliced into the SQL."""
    captured: dict[str, object] = {}
    _db_returning(_proc(stdout=""), captured).recent_start_times(7)
    argv = captured["argv"]
    assert isinstance(argv, list)
    assert "uid=7" in argv
    assert "ON_ERROR_STOP=1" in argv
    # The statement itself carries no interpolated id.
    assert "7" not in str(captured["stdin"])
    assert ":uid" in str(captured["stdin"])


def test_container_name_defaults_and_overrides() -> None:
    assert db_lookup.EndurainDatabase()._container == "endurain-postgres"
    assert db_lookup.EndurainDatabase(container="other")._container == "other"


def test_container_name_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(db_lookup._CONTAINER_ENV, "from-env")
    assert db_lookup.EndurainDatabase()._container == "from-env"


def test_default_runner_executes_subprocess(monkeypatch: pytest.MonkeyPatch) -> None:
    """The real _run is otherwise unreachable in a unit test."""
    seen: dict[str, object] = {}

    def _fake_run(argv: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        seen["argv"] = argv
        seen["input"] = kwargs.get("input")
        return _proc(stdout="")

    monkeypatch.setattr(subprocess, "run", _fake_run)
    assert db_lookup._run(["docker", "true"], "SELECT 1;").returncode == 0
    assert seen["argv"] == ["docker", "true"]
    assert seen["input"] == "SELECT 1;"
