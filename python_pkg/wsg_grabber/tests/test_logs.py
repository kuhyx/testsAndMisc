"""Tests for the structured event log."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from python_pkg.wsg_grabber import logs

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


@pytest.fixture(autouse=True)
def _closed() -> Iterator[None]:
    """Make sure no test leaves the log file open.

    Yields:
        None: Control returns to the test.
    """
    try:
        yield
    finally:
        logs.stop()


def _records(path: Path) -> list[dict[str, object]]:
    """Parse a session log.

    Args:
        path: The JSONL file.

    Returns:
        list[dict[str, object]]: One dict per line.
    """
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


def test_starting_creates_a_log_and_announces_itself(tmp_path: Path) -> None:
    path = logs.start()
    assert path.parent == logs.logs_dir()
    assert str(path).startswith(str(tmp_path))
    assert logs.current_path() == path

    first = _records(path)[0]
    assert first["event"] == "session.start"
    assert first["seq"] == 1
    assert first["level"] == "info"


def test_every_record_carries_the_standard_fields() -> None:
    path = logs.start()
    logs.event("thing.happened", detail="x", count=3)
    record = _records(path)[-1]
    assert set(record) >= {"ts", "seq", "level", "event", "thread"}
    assert record["event"] == "thing.happened"
    assert record["detail"] == "x"
    assert record["count"] == 3


def test_sequence_numbers_are_monotonic() -> None:
    path = logs.start()
    for index in range(5):
        logs.event("tick", index=index)
    seqs = [int(str(record["seq"])) for record in _records(path)]
    assert seqs == sorted(seqs)
    assert len(set(seqs)) == len(seqs)


def test_level_helpers_set_the_level() -> None:
    path = logs.start("debug")
    logs.debug("a")
    logs.warning("b")
    logs.error("c")
    levels = [record["level"] for record in _records(path)[1:]]
    assert levels == ["debug", "warning", "error"]


def test_records_below_the_threshold_are_dropped() -> None:
    path = logs.start("warning")
    logs.debug("dropped")
    logs.event("also-dropped")
    logs.warning("kept")
    events = [record["event"] for record in _records(path)]
    assert "dropped" not in events
    assert "also-dropped" not in events
    assert "kept" in events


def test_an_unknown_level_name_falls_back_to_info() -> None:
    path = logs.start("nonsense")
    logs.event("recorded", level="nonsense")
    assert any(record["event"] == "recorded" for record in _records(path))


def test_values_that_cannot_be_serialised_are_stringified() -> None:
    path = logs.start()
    logs.event("odd", value=object(), where=tmp_marker())
    record = _records(path)[-1]
    assert isinstance(record["value"], str)


def tmp_marker() -> object:
    """Return a non-JSON-encodable value.

    Returns:
        object: Something json cannot encode directly.
    """
    return {1, 2, 3}


def test_events_before_start_go_nowhere_and_do_not_raise() -> None:
    logs.stop()
    logs.event("ignored")
    assert logs.current_path() is None


def test_echo_mirrors_records_to_stderr(
    capsys: pytest.CaptureFixture[str],
) -> None:
    logs.start(echo=True)
    logs.event("mirrored", detail="yes")
    captured = capsys.readouterr().err
    assert "mirrored" in captured
    assert json.loads(captured.strip().splitlines()[-1])["detail"] == "yes"


def test_starting_twice_rotates_to_a_new_file() -> None:
    first = logs.start()
    logs.event("one")
    second = logs.start()
    logs.event("two")
    assert logs.current_path() == second
    assert "one" in first.read_text(encoding="utf-8")


def test_stop_is_idempotent() -> None:
    logs.start()
    logs.stop()
    logs.stop()
    assert logs.current_path() is None


def test_the_log_lands_inside_the_sandbox(tmp_path: Path) -> None:
    """The suite must never write a log into the real data directory."""
    assert str(logs.logs_dir()).startswith(str(tmp_path))


def test_each_session_numbers_its_own_records_from_one() -> None:
    """seq orders records within one file, so it must restart per session."""
    first = logs.start()
    logs.event("a")
    logs.event("b")
    second = logs.start()
    assert _records(second)[0]["seq"] == 1
    assert len(_records(first)) == 3
