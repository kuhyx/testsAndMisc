from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from python_pkg.token_audit import parse

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


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


def test_load_session_reads_usage_and_cwd(tmp_path: Path) -> None:
    path = _write(tmp_path, [_assistant(usage={"output_tokens": 3})])
    session = parse.load_session(path)
    assert session.cwd == "/home/kuhy/demo"
    assert session.turn_count == 1
    assert session.turns[0].model == "claude-opus-5"


def test_context_is_cache_read_plus_creation(tmp_path: Path) -> None:
    usage = {"cache_read_input_tokens": 40, "cache_creation_input_tokens": 2}
    path = _write(tmp_path, [_assistant(usage=usage)])
    assert parse.load_session(path).turns[0].context == 42


def test_malformed_lines_are_skipped_not_fatal(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        [
            "{not json",
            "[1,2,3]",
            "null",
            json.dumps(_assistant(usage={"output_tokens": 1})),
        ],
    )
    assert parse.load_session(path).turn_count == 1


def test_tool_result_is_joined_to_its_tool_use(tmp_path: Path) -> None:
    records = [
        _assistant(
            content=[
                {
                    "type": "tool_use",
                    "id": "t1",
                    "name": "Read",
                    "input": {"file_path": "/x/shot.png"},
                },
            ],
        ),
        {
            "message": {
                "content": [
                    {"type": "tool_result", "tool_use_id": "t1", "content": "abcdefgh"}
                ]
            }
        },
    ]
    session = parse.load_session(_write(tmp_path, records))
    assert len(session.tools) == 1
    call = session.tools[0]
    assert call.name == "Read"
    assert call.path == "/x/shot.png"
    assert call.is_image


def test_orphan_tool_result_is_ignored(tmp_path: Path) -> None:
    records = [
        {"message": {"content": [{"type": "tool_result", "tool_use_id": "nope"}]}}
    ]
    assert parse.load_session(_write(tmp_path, records)).tools == []


def test_skill_input_is_captured(tmp_path: Path) -> None:
    records = [
        _assistant(
            content=[
                {
                    "type": "tool_use",
                    "id": "s1",
                    "name": "Skill",
                    "input": {"skill": "finish"},
                },
            ],
        ),
        {
            "message": {
                "content": [
                    {"type": "tool_result", "tool_use_id": "s1", "content": "ok"}
                ]
            }
        },
    ]
    assert parse.load_session(_write(tmp_path, records)).tools[0].skill == "finish"


def test_tool_use_without_id_or_dict_input_is_tolerated(tmp_path: Path) -> None:
    records = [
        _assistant(content=[{"type": "tool_use", "name": "Read"}]),
        _assistant(
            content=[
                {"type": "tool_use", "id": "t2", "name": "Bash", "input": "notadict"}
            ],
        ),
        {"message": {"content": [{"type": "tool_result", "tool_use_id": "t2"}]}},
    ]
    session = parse.load_session(_write(tmp_path, records))
    assert session.tools[0].name == "Bash"
    assert session.tools[0].path is None
    assert session.tools[0].result_tokens == 0


def test_non_dict_messages_and_content_are_ignored(tmp_path: Path) -> None:
    records = [
        {"message": "a string"},
        {"message": {"content": "not a list"}},
        {"message": {"usage": "not a dict"}},
        {"no_message": True},
        {"message": {"content": ["not a dict block"]}},
    ]
    session = parse.load_session(_write(tmp_path, records))
    assert session.turn_count == 0
    assert session.tools == []


def test_model_falls_back_to_unknown(tmp_path: Path) -> None:
    records = [{"message": {"usage": {"output_tokens": 1}}}]
    assert parse.load_session(_write(tmp_path, records)).turns[0].model == "unknown"


def test_non_string_model_falls_back(tmp_path: Path) -> None:
    records = [{"message": {"usage": {"output_tokens": 1}, "model": 42}}]
    assert parse.load_session(_write(tmp_path, records)).turns[0].model == "unknown"


def test_tool_use_with_non_string_id_is_dropped(tmp_path: Path) -> None:
    records = [
        _assistant(
            content=[{"type": "tool_use", "id": 99, "name": "Read", "input": {}}]
        ),
        {"message": {"content": [{"type": "tool_result", "tool_use_id": 99}]}},
    ]
    assert parse.load_session(_write(tmp_path, records)).tools == []


def test_unrecognised_block_types_are_ignored(tmp_path: Path) -> None:
    records = [_assistant(content=[{"type": "text", "text": "hello"}])]
    session = parse.load_session(_write(tmp_path, records))
    assert session.tools == []
    assert session.turn_count == 0


def test_load_session_ignores_events_of_other_types(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _write(tmp_path, [_assistant(usage={"output_tokens": 1})])
    monkeypatch.setattr(parse, "iter_events", lambda _: iter([("turn", "not a Turn")]))
    session = parse.load_session(path)
    assert session.turns == []
    assert session.tools == []


def test_cwd_none_when_absent(tmp_path: Path) -> None:
    records = [{"message": {"usage": {"output_tokens": 1}}}]
    assert parse.load_session(_write(tmp_path, records)).cwd is None


def test_usage_keeps_only_integer_fields(tmp_path: Path) -> None:
    usage = {"output_tokens": 5, "service_tier": "standard", "iterations": [{}]}
    session = parse.load_session(_write(tmp_path, [_assistant(usage=usage)]))
    assert session.turns[0].usage == {"output_tokens": 5}


def test_sidechain_flag_is_preserved(tmp_path: Path) -> None:
    path = _write(tmp_path, [_assistant(usage={"output_tokens": 1}, sidechain=True)])
    assert parse.load_session(path).turns[0].is_sidechain
