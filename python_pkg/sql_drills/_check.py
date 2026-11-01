"""Grade one query: fresh database, drill schema, user's SQL, exact compare."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from python_pkg.sql_drills import _engine
from python_pkg.sql_drills._normalize import diff, normalize

if TYPE_CHECKING:
    from pathlib import Path

    from python_pkg.sql_drills._drills import Drill


@dataclass(frozen=True)
class CheckResult:
    """``status`` is ``pass``, ``fail`` (wrong output) or ``error``."""

    status: str
    message: str


class _StepError(Exception):
    """A pipeline step failed; the message is shown to the user."""


def _step(result: _engine.SqlResult, what: str) -> str:
    """Return stdout of a successful step or raise with its stderr."""
    if result.returncode != 0:
        msg = f"{what}: {result.stderr.strip()}"
        raise _StepError(msg)
    return result.stdout


def _execute(drill: Drill, query_file: Path) -> str:
    """Fresh DB, drill schema, then the user's SQL; return the raw output."""
    if not _engine.is_ready():
        msg = "MySQL is not running; run `start` first"
        raise _StepError(msg)
    if not query_file.is_file():
        msg = f"query file not found: {query_file}"
        raise _StepError(msg)
    db = f"drill_{drill.id}"
    reset = _engine.run_sql(f"DROP DATABASE IF EXISTS {db}; CREATE DATABASE {db};")
    _step(reset, "could not reset database")
    _step(_engine.run_sql(drill.schema.read_text(), database=db), "drill schema failed")
    result = _engine.run_sql(query_file.read_text(), database=db)
    return _step(result, "SQL error")


def run_check(drill: Drill, query_file: Path) -> CheckResult:
    """Load the drill into a fresh DB, run the query, compare to expected."""
    try:
        output = _execute(drill, query_file)
    except _StepError as exc:
        return CheckResult("error", str(exc))
    expected = normalize(drill.expected.read_text())
    actual = normalize(output)
    if expected == actual:
        return CheckResult("pass", f"PASS {drill.id} ({len(actual)} rows)")
    return CheckResult(
        "fail",
        f"FAIL {drill.id}: expected {len(expected)} rows, got {len(actual)}\n"
        f"{diff(expected, actual)}",
    )
