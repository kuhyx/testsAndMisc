"""Live E2E against the real container; skipped when it is not running.

Start it first with ``python3 -m python_pkg.sql_drills start``. These tests are
the only place reference solutions are used, so learning mode never shows them.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from python_pkg.sql_drills import _check, _drills, _engine

SOLUTIONS = Path(__file__).parent / "solutions"
DRILL_IDS = [d.id for d in _drills.list_drills()]


def _engine_up() -> bool:
    try:
        return _engine.is_ready()
    except _engine.EngineError:
        return False


pytestmark = [
    pytest.mark.docker,
    pytest.mark.skipif(not _engine_up(), reason="sql-drills-mysql is not running"),
]


@pytest.mark.parametrize("drill_id", DRILL_IDS)
def test_reference_solution_matches_expected(drill_id: str) -> None:
    result = _check.run_check(
        _drills.get_drill(drill_id), SOLUTIONS / f"{drill_id}.sql"
    )
    assert result.status == "pass", result.message


def test_wrong_query_fails_with_diff(tmp_path: Path) -> None:
    query = tmp_path / "q.sql"
    query.write_text("SELECT region, 1, 2, 3, 4 FROM shop_sales GROUP BY region;")
    result = _check.run_check(_drills.get_drill("01"), query)
    assert result.status == "fail"
    assert "expected:" in result.message


def test_syntax_error_is_error(tmp_path: Path) -> None:
    query = tmp_path / "q.sql"
    query.write_text("SELECT * FROM;")
    result = _check.run_check(_drills.get_drill("01"), query)
    assert result.status == "error"
    assert "1064" in result.message


def test_checks_are_isolated(tmp_path: Path) -> None:
    query = tmp_path / "q.sql"
    query.write_text("DELETE FROM shop_sales;")
    _check.run_check(_drills.get_drill("01"), query)
    again = _check.run_check(_drills.get_drill("01"), SOLUTIONS / "01_pivot_sum.sql")
    assert again.status == "pass"
