"""Per-call and per-turn detail rows the walker keeps."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from python_pkg.token_dashboard import detail
from python_pkg.token_dashboard.tests.conftest import (
    assistant,
    iso,
    prompt,
    result,
    use,
    walk_detail,
)

if TYPE_CHECKING:
    from pathlib import Path

ONE_HOUR_WRITE = {
    "cache_creation_input_tokens": 1000,
    "cache_creation": {"ephemeral_1h_input_tokens": 1000},
}


def test_result_creation_and_carry_are_priced_by_hand(tmp_path: Path) -> None:
    rows = walk_detail(
        tmp_path,
        [
            prompt("go", 0),
            assistant("m1", 2, blocks=[use("t1", "Bash", command="git status")]),
            result("t1", 5, "x" * 398),  # json.dumps -> 400 chars -> 100 tokens
            assistant("m2", 9, **ONE_HOUR_WRITE),
            assistant("m3", 12, context=2000),
        ],
    )
    (call,) = rows.calls
    assert (call.family, call.target, call.batch) == ("git status", "git status", 1)
    assert call.result_tokens == 100
    assert call.end_ts - call.where.ts == pytest.approx(3)
    # Written once by m2 at the 1h rate (2x input $4/MTok) ...
    assert call.cost.create_usd == pytest.approx(100 * 2.0 * 4 / 1e6)
    # ... then cache-read by m2 and m3 at $0.20/MTok.
    assert call.cost.carry_usd == pytest.approx(100 * 2 * 0.2 / 1e6)
    assert call.cost.carry_calls == 2
    assert call.where.model == "claude-opus-5-5"


def test_compaction_stops_the_carry(tmp_path: Path) -> None:
    boundary = {
        "type": "system",
        "subtype": "compact_boundary",
        "timestamp": iso(4),
        "compactMetadata": {
            "trigger": "auto",
            "preTokens": 100000,
            "postTokens": 9000,
            "durationMs": 5000,
        },
    }
    read = use("t1", "Read", file_path="/a")
    rows = walk_detail(
        tmp_path,
        [
            prompt("go", 0),
            assistant("m1", 1, blocks=[read], context=100000),
            result("t1", 2, "x" * 398),
            assistant("m2", 3, context=100000),
            boundary,
            assistant("m3", 5, context=9000),
        ],
    )
    assert rows.calls[0].cost.carry_calls == 1
    (mark,) = [m for m in rows.marks if m.kind == "compaction"]
    assert (mark.name, mark.tokens, mark.extra) == ("auto", 100000, 9000)
    assert mark.duration_ms == 5000
    assert mark.cost.carry_usd == 0  # the summary call is not context


def test_batch_errors_images_and_signatures(tmp_path: Path) -> None:
    image = {"type": "image", "source": {"type": "base64", "data": "A" * 9000}}
    blocks = [use("a", "Bash", command="ls"), use("b", "mcp__chrome__shot")]
    failed = {
        "type": "tool_result",
        "tool_use_id": "a",
        "content": "Exit code 2",
        "is_error": True,
    }
    shot = {
        "type": "tool_result",
        "tool_use_id": "b",
        "content": [image, {"type": "text", "text": "ok"}],
    }
    rows = walk_detail(
        tmp_path,
        [
            prompt("go", 0),
            assistant("m1", 1, blocks=blocks[:1]),
            assistant("m1", 1, blocks=blocks[1:]),
            {"type": "user", "timestamp": iso(2), "message": {"content": [failed]}},
            {"type": "user", "timestamp": iso(3), "message": {"content": [shot]}},
            assistant("m2", 4),
        ],
    )
    by_name = {c.name: c for c in rows.calls}
    assert {c.batch for c in rows.calls} == {2}
    assert by_name["Bash"].error_kind == "exit_code"
    found = by_name["mcp__chrome__shot"]
    assert (found.family, found.target, found.images) == ("mcp:chrome", "shot", 1)
    assert found.error_kind == ""
    assert found.result_tokens < 3000  # an image is priced by area, not base64
    assert by_name["Bash"].sig != found.sig


def test_turn_detail_latency_cache_split_and_output_split(tmp_path: Path) -> None:
    text = {"type": "text", "text": "y" * 400}  # ~100 tokens of reply
    thinking = {"type": "thinking", "thinking": ""}
    rows = walk_detail(
        tmp_path,
        [
            prompt("go", 0),
            assistant("m1", 7, **ONE_HOUR_WRITE, blocks=[thinking]),
            assistant("m1", 8, blocks=[text]),
            assistant("m2", 9, output=10, blocks=[text]),
            assistant("m3", 10, output=50, blocks=[{"type": "server_tool_use"}]),
            assistant("m4", 11, output=40, blocks=[thinking]),
        ],
    )
    first, second, third, fourth = rows.turns
    assert first.latency_s == pytest.approx(7)
    assert (first.cw_1h, first.cw_5m) == (1000, 0)
    assert (first.out_text, first.out_tool, first.out_think) == (100, 0, 900)
    # More visible text than billed output: scaled down, no thinking left.
    assert (second.out_text, second.out_think) == (10, 0)
    assert second.latency_s == pytest.approx(1)
    # Nothing visible: all of it is text, or thinking when a block says so.
    assert (third.out_text, third.out_think) == (50, 0)
    assert (fourth.out_text, fourth.out_think) == (0, 40)


def test_text_and_tool_output_without_thinking_split_by_length(
    tmp_path: Path,
) -> None:
    blocks = [{"type": "text", "text": "y" * 400}, use("t", "Bash", command="z" * 385)]
    rows = walk_detail(
        tmp_path, [prompt("go", 0), assistant("m1", 1, output=1000, blocks=blocks)]
    )
    (turn,) = rows.turns
    assert (turn.out_text, turn.out_tool, turn.out_think) == (500, 500, 0)
    assert turn.tool_calls == 1


def test_write_multiplier_blends_the_split() -> None:
    assert detail.write_multiplier({}) == pytest.approx(1.25)
    half = {"cache_creation_input_tokens": 100, "cache_creation_1h": 50}
    assert detail.write_multiplier(half) == pytest.approx((50 * 2 + 50 * 1.25) / 100)


def test_result_for_an_unknown_call_is_ignored() -> None:
    found = detail.Detail()
    found.result({"tool_use_id": "nope", "content": "x"}, 1.0)
    assert found.rows.calls == []
