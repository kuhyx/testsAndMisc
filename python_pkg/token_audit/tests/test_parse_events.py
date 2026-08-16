"""Tests for token_audit event iteration and transcript discovery."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from python_pkg.token_audit import parse
from python_pkg.token_audit.model import ToolCall, Turn

if TYPE_CHECKING:
    from pathlib import Path


def _assistant(
    usage: dict[str, int] | None = None,
    content: list[dict[str, object]] | None = None,
    cwd: str = "/home/kuhy/demo",
    *,
    sidechain: bool = False,
) -> dict[str, object]:
    message: dict[str, object] = {"model": "claude-opus-5"}
    if usage is not None:
        message["usage"] = usage
    if content is not None:
        message["content"] = content
    return {
        "type": "assistant",
        "cwd": cwd,
        "isSidechain": sidechain,
        "message": message,
    }


def _write(tmp_path: Path, records: list[object], name: str = "sess.jsonl") -> Path:
    path = tmp_path / name
    path.write_text(
        "\n".join(json.dumps(r) if isinstance(r, dict) else r for r in records),
        encoding="utf-8",
    )
    return path


def test_iter_events_preserves_order(tmp_path: Path) -> None:
    records = [
        _assistant(
            content=[
                {
                    "type": "tool_use",
                    "id": "a",
                    "name": "Read",
                    "input": {"file_path": "/i.png"},
                },
            ],
        ),
        {
            "message": {
                "content": [
                    {"type": "tool_result", "tool_use_id": "a", "content": "xxxx"}
                ]
            }
        },
        _assistant(usage={"output_tokens": 1}),
    ]
    kinds = [k for k, _ in parse.iter_events(_write(tmp_path, records))]
    assert kinds == ["tool", "turn"]


def test_events_carry_expected_types(tmp_path: Path) -> None:
    records = [
        _assistant(
            content=[
                {"type": "tool_use", "id": "a", "name": "Read", "input": {}},
            ],
        ),
        {"message": {"content": [{"type": "tool_result", "tool_use_id": "a"}]}},
        _assistant(usage={"output_tokens": 1}),
    ]
    events = dict(parse.iter_events(_write(tmp_path, records)))
    assert isinstance(events["tool"], ToolCall)
    assert isinstance(events["turn"], Turn)


def test_find_transcripts_filters_by_window(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    old = project / "old.jsonl"
    new = project / "new.jsonl"
    old.write_text("{}", encoding="utf-8")
    new.write_text("{}", encoding="utf-8")
    import os

    os.utime(old, (1000, 1000))
    os.utime(new, (50_000, 50_000))

    assert parse.find_transcripts(tmp_path, since=10_000) == [new]
    assert parse.find_transcripts(tmp_path, since=0, until=2000) == [old]
    assert len(parse.find_transcripts(tmp_path, since=0)) == 2


@pytest.mark.parametrize("payload", [None, "abcdefgh"])
def test_result_tokens_handles_missing_content(payload: str | None) -> None:
    assert parse._result_tokens({"content": payload}) >= 0
