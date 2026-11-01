"""Drill discovery and rendering over the bundled drills."""

from __future__ import annotations

from pathlib import Path

import pytest

from python_pkg.sql_drills import _drills

SOLUTIONS = Path(__file__).parent / "solutions"


def test_drills_are_listed_in_priority_order() -> None:
    ids = [d.id for d in _drills.list_drills()]
    assert ids == sorted(ids)
    assert len(ids) >= 10


def test_every_drill_has_all_parts_and_a_reference() -> None:
    for d in _drills.list_drills():
        assert d.schema.read_text().strip(), d.id
        assert d.task.read_text().strip(), d.id
        assert d.expected.read_text().strip(), d.id
        assert (SOLUTIONS / f"{d.id}.sql").is_file(), d.id


def test_get_by_full_id_and_by_number_prefix() -> None:
    first = _drills.list_drills()[0]
    assert _drills.get_drill(first.id) == first
    assert _drills.get_drill(first.id.split("_")[0]) == first


def test_unknown_drill_raises() -> None:
    with pytest.raises(_drills.UnknownDrillError):
        _drills.get_drill("nope")


def test_show_has_task_schema_and_sample_but_no_solution() -> None:
    d = _drills.list_drills()[0]
    text = _drills.render_show(d)
    assert d.task.read_text().strip() in text
    assert "CREATE TABLE" in text
    first_expected = d.expected.read_text().splitlines()[0]
    assert first_expected in text
    assert (SOLUTIONS / f"{d.id}.sql").read_text().strip() not in text


def test_show_truncates_long_expected_output(tmp_path: Path) -> None:
    exp = tmp_path / "expected.txt"
    exp.write_text("\n".join(f"row{i}" for i in range(20)) + "\n")
    task = tmp_path / "DOCS-task.md"
    task.write_text("T")
    schema = tmp_path / "schema.sql"
    schema.write_text("S")
    text = _drills.render_show(_drills.Drill("x", task, schema, exp))
    assert "row0" in text
    assert "row19" not in text
    assert "20 rows in total" in text


def test_title_is_first_heading() -> None:
    d = _drills.list_drills()[0]
    assert _drills.title_of(d) == d.task.read_text().splitlines()[0].lstrip("# ")


def test_missing_drills_dir_lists_nothing(tmp_path: Path) -> None:
    assert _drills.list_drills(tmp_path / "absent") == []
