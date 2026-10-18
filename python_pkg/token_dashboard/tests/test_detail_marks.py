"""Context marks: hooks, injected attachments, API errors, interruptions."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from python_pkg.token_dashboard.tests.conftest import (
    BASE,
    assistant,
    attach,
    iso,
    prompt,
    result,
    use,
    walk_detail,
)

if TYPE_CHECKING:
    from pathlib import Path

CTX = "cd chain wrapped in a subshell"


def _hook_records() -> list[dict[str, object]]:
    run = {"type": "hook_success", "hookName": "PreToolUse:Bash"}
    run |= {"hookEvent": "PreToolUse", "toolUseID": "t1", "content": ""}
    stop = {"blockingError": "no status tag", "command": "python3 /h/tag_stop.py"}
    return [
        attach(
            0,
            type="hook_success",
            hookName="SessionStart:startup",
            hookEvent="SessionStart",
            toolUseID="s",
            content="x" * 400,
            stdout="x" * 400,
            command="bash /h/.claude/hooks/start.sh",
            durationMs=30,
        ),
        prompt("go", 1),
        assistant("m1", 2, blocks=[use("t1", "Bash", command="cd /x && ls")]),
        attach(
            3,
            type="hook_additional_context",
            hookName="PreToolUse:Bash",
            hookEvent="PreToolUse",
            toolUseID="t1",
            content=[CTX],
        ),
        attach(
            3,
            **run,
            stdout='{"additionalContext":"' + CTX + '"}',
            command="bash /h/.claude/hooks/cd_chain.sh",
            durationMs=15,
        ),
        attach(3, **run, stdout="{}", command="bash /h/other.sh", durationMs="7"),
        result("t1", 4),
        assistant("m2", 5),
        attach(
            6,
            type="hook_blocking_error",
            hookName="Stop",
            toolUseID="z",
            blockingError=stop,
        ),
        assistant("m3", 7, output=500),
        assistant("m4", 8, output=500),
        prompt("next", 20),
        assistant("m5", 21),
        attach(22, type="hook_system_message", hookName="UserPromptSubmit"),
        attach(
            22, type="hook_non_blocking_error", hookName="PostToolUse", content="oops"
        ),
        attach(22, type="nested_memory", path="/r/CLAUDE.md", content={"c": "z"}),
        attach(22, type="prompt_snapshot", systemPrompt=["huge"]),
    ]


def test_hooks_are_marked_matched_and_their_retry_priced(tmp_path: Path) -> None:
    rows = walk_detail(tmp_path, _hook_records())
    marks = {(m.kind, m.detail): m for m in rows.marks}
    start = marks[("hook_run", "start.sh")]
    assert (start.tokens, start.duration_ms, start.where.prompt_idx) == (100, 30, -1)
    assert start.cost.carry_usd > 0
    assert start.where.model == "claude-opus-5-5"  # filled from the first turn
    assert marks[("hook_context", "cd_chain.sh")].tokens == len(CTX) // 4
    assert marks[("hook_run", "other.sh")].duration_ms == 7
    assert marks[("hook_run", "cd_chain.sh")].tokens == 0  # JSON is not injected
    bounce = marks[("hook_block", "tag_stop.py")]
    assert bounce.name == "Stop"
    assert bounce.retry_usd == pytest.approx(2 * 500 * 20 / 1e6)  # m3 + m4 only
    assert ("hook_msg", "") in marks
    assert marks[("hook_error", "")].tokens == 1
    assert marks[("attach", "/r/CLAUDE.md")].name == "nested_memory"
    assert not [m for m in rows.marks if m.name == "prompt_snapshot"]


def test_pretool_block_retry_is_only_the_next_call(tmp_path: Path) -> None:
    rows = walk_detail(
        tmp_path,
        [
            prompt("go", 0),
            assistant("m1", 1),
            attach(
                2,
                type="hook_blocking_error",
                hookName="PreToolUse:Bash",
                toolUseID="q",
                blockingError="denied",
            ),
            assistant("m2", 3, output=100),
            assistant("m3", 4, output=100),
        ],
    )
    (block,) = rows.marks
    assert (block.detail, block.tokens) == ("", 1)
    assert block.retry_usd == pytest.approx(100 * 20 / 1e6)


def test_api_errors_interruptions_and_pasted_images(tmp_path: Path) -> None:
    pasted = {"type": "image", "source": {"type": "base64", "data": "A"}}
    limit = {"isApiErrorMessage": True, "error": "rate_limit"}
    limit |= {"apiError": "usage_limit_reached"}
    text = [{"type": "text", "text": "Overloaded"}]
    rows = walk_detail(
        tmp_path,
        [
            {
                "type": "user",
                "timestamp": iso(0),
                "message": {"content": [{"type": "text", "text": "look"}, pasted]},
            },
            {"type": "assistant", "timestamp": iso(1), **limit, "message": {}},
            {
                "type": "assistant",
                "timestamp": iso(2),
                "isApiErrorMessage": True,
                "message": {"content": text},
            },
            {
                "type": "user",
                "timestamp": iso(3),
                "message": {
                    "content": [
                        {"type": "text", "text": "[Request interrupted by user]"}
                    ]
                },
            },
            assistant("m1", 4),
        ],
    )
    kinds = sorted((m.kind, m.name, m.detail) for m in rows.marks)
    assert kinds == [
        ("api_error", "rate_limit", "usage_limit_reached"),
        ("api_error", "unknown", "Overloaded"),
        ("image", "user", ""),
        ("interrupt", "user", ""),
    ]
    assert rows.marks[0].where.ts == pytest.approx(BASE)
    assert rows.marks[0].tokens > 0


def test_repeats_merge_and_odd_records_are_tolerated(tmp_path: Path) -> None:
    reminder = {"type": "total_tokens_reminder", "left": 5}
    odd = {"hookName": "PostToolUse", "toolUseID": "u"}
    rows = walk_detail(
        tmp_path,
        [
            prompt("go", 0),
            attach(1, **reminder),
            attach(2, **reminder),
            attach(
                2,
                type="hook_success",
                **odd,
                content="",
                stdout="",
                command="",
                durationMs="n/a",
            ),
            attach(2, type="hook_additional_context", **odd, content=""),
            attach(2, type="hook_additional_context", **odd, content="unmatched"),
            attach(2, type="hook_cancelled", **odd),
            {"type": "system", "subtype": "turn_duration", "timestamp": iso(2)},
            assistant("m1", 3, blocks=[{"type": "server_tool_use", "id": "w"}]),
        ],
    )
    (merged,) = [m for m in rows.marks if m.name == "total_tokens_reminder"]
    assert merged.count == 2
    assert merged.where.ts == pytest.approx(BASE + 1)
    assert merged.cost.carry_calls == 2
    run = next(m for m in rows.marks if m.kind == "hook_run")
    assert (run.duration_ms, run.detail) == (0, "")
    contexts = [m for m in rows.marks if m.kind == "hook_context"]
    assert {m.detail for m in contexts} == {""}
