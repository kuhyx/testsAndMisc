from __future__ import annotations

import pytest

from python_pkg.token_audit import records
from python_pkg.token_audit.model import Turn


def _turn(
    message_id: str = "m1",
    usage: dict[str, int] | None = None,
    context: int = 0,
    tool_calls: int = 0,
) -> Turn:
    return Turn(
        usage=usage or {},
        context=context,
        model="claude-opus-5",
        is_sidechain=False,
        message_id=message_id,
        tool_calls=tool_calls,
    )


@pytest.mark.parametrize(
    "record",
    [{}, {"timestamp": 5}, {"timestamp": "not a date"}],
)
def test_timestamp_none_for_missing_or_bad(record: dict[str, object]) -> None:
    assert records.timestamp(record) is None


def test_timestamp_parses_iso() -> None:
    stamp = records.timestamp({"timestamp": "1970-01-02T00:00:00+00:00"})
    assert stamp == 86400.0


def test_in_window_rules() -> None:
    dated = {"timestamp": "1970-01-01T00:01:40+00:00"}  # 100s
    assert records.in_window(dated, None)
    assert records.in_window({}, (0.0, 1.0))
    assert records.in_window(dated, (100.0, 100.0))
    assert not records.in_window(dated, (101.0, 200.0))
    assert not records.in_window(dated, (0.0, 99.0))


def test_cache_split_reads_both_classes() -> None:
    usage = {
        "cache_creation": {
            "ephemeral_1h_input_tokens": 7,
            "ephemeral_5m_input_tokens": 3,
        },
    }
    assert records.cache_split(usage) == {
        records.CACHE_1H: 7,
        records.CACHE_5M: 3,
    }


def test_cache_split_ignores_non_dict_and_non_int() -> None:
    assert records.cache_split({"cache_creation": 4}) == {}
    nested = {"cache_creation": {"ephemeral_1h_input_tokens": "x"}}
    assert records.cache_split(nested) == {}


def test_merge_takes_max_usage_and_sums_tools() -> None:
    held = _turn(usage={"output_tokens": 1, "input_tokens": 5}, context=3, tool_calls=1)
    extra = _turn(
        usage={"output_tokens": 9, "cache_read_input_tokens": 2},
        context=1,
        tool_calls=2,
    )
    merged = records.merge(held, extra)
    assert merged.usage == {
        "output_tokens": 9,
        "input_tokens": 5,
        "cache_read_input_tokens": 2,
    }
    assert merged.context == 3
    assert merged.tool_calls == 3


def test_merger_collapses_consecutive_same_id() -> None:
    merger = records.TurnMerger()
    assert merger.push(_turn("a", {"output_tokens": 1})) is None
    assert merger.push(_turn("a", {"output_tokens": 4})) is None
    done = merger.push(_turn("b"))
    assert done is not None
    assert done.usage == {"output_tokens": 4}
    last = merger.flush()
    assert last is not None
    assert last.message_id == "b"
    assert merger.flush() is None


def test_merger_drops_late_repeat_of_seen_id() -> None:
    merger = records.TurnMerger()
    merger.push(_turn("a"))
    merger.push(_turn("b"))
    # "a" already seen and not the held turn: dropped, "b" is released.
    done = merger.push(_turn("a"))
    assert done is not None
    assert done.message_id == "b"
    assert merger.flush() is None


def test_merger_keeps_every_idless_turn() -> None:
    merger = records.TurnMerger()
    assert merger.push(_turn("")) is None
    first = merger.push(_turn(""))
    assert first is not None
    last = merger.flush()
    assert last is not None
