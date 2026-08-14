from __future__ import annotations

import pytest

from python_pkg.token_audit.model import (
    COMPACTION_DROP_RATIO,
    WEIGHTS,
    Session,
    ToolCall,
    Turn,
    weighted,
)


def test_weights_price_output_highest() -> None:
    assert WEIGHTS["output_tokens"] > WEIGHTS["input_tokens"]
    assert WEIGHTS["cache_read_input_tokens"] < WEIGHTS["input_tokens"]
    assert 0 < COMPACTION_DROP_RATIO < 1


def test_weighted_applies_each_multiplier() -> None:
    usage = {
        "input_tokens": 10,
        "cache_creation_input_tokens": 100,
        "cache_read_input_tokens": 1000,
        "output_tokens": 1,
    }
    assert weighted(usage) == pytest.approx(10 + 125 + 100 + 5)


def test_weighted_treats_missing_kinds_as_zero() -> None:
    assert weighted({}) == 0.0


def test_turn_cost_delegates_to_weighted() -> None:
    turn = Turn(usage={"output_tokens": 2}, context=0, model="m", is_sidechain=False)
    assert turn.cost == pytest.approx(10.0)


@pytest.mark.parametrize("path", ["/a/b.png", "/a/b.PNG", "/a/b.jpeg"])
def test_tool_call_detects_images(path: str) -> None:
    assert ToolCall(name="Read", result_tokens=1, path=path).is_image


@pytest.mark.parametrize("path", ["/a/b.py", "/a/noextension", None])
def test_tool_call_rejects_non_images(path: str | None) -> None:
    assert not ToolCall(name="Read", result_tokens=1, path=path).is_image


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("mcp__aseprite__draw_line", "aseprite"),
        ("mcp__i3wm__get_tree", "i3wm"),
        ("Read", None),
        ("mcp__broken", None),
    ],
)
def test_tool_call_mcp_server(name: str, expected: str | None) -> None:
    assert ToolCall(name=name, result_tokens=0).mcp_server == expected


def _turn(context: int, out: int = 0, read: int = 0, create: int = 0) -> Turn:
    return Turn(
        usage={
            "output_tokens": out,
            "cache_read_input_tokens": read,
            "cache_creation_input_tokens": create,
        },
        context=context,
        model="m",
        is_sidechain=False,
    )


def test_session_aggregates() -> None:
    session = Session(session_id="s", path="p")
    session.turns = [_turn(100, out=1), _turn(500, out=2)]
    assert session.turn_count == 2
    assert session.max_context == 500
    assert session.cost == pytest.approx(15.0)


def test_session_empty_has_zero_max_context() -> None:
    assert Session(session_id="s", path="p").max_context == 0


def test_cold_start_counts_only_turns_with_no_cache_read() -> None:
    session = Session(session_id="s", path="p")
    session.turns = [
        _turn(0, create=5000),  # cold: nothing to read yet
        _turn(9, read=9, create=100),  # warm: excluded
    ]
    assert session.cold_start_tokens == 5000
