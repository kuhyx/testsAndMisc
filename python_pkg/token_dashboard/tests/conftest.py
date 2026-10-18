"""Shared dashboard test setup: source isolation and transcript builders.

The autouse fixture keeps every test away from the real ``~/.claude`` state;
the builders below make synthetic transcript records.
"""

from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import TYPE_CHECKING, Any

import pytest

from python_pkg.token_dashboard import ab, aux, context_files, walk

if TYPE_CHECKING:
    from pathlib import Path

    from python_pkg.token_dashboard.detail_rows import DetailRows

BASE = 1_791_600_000.0  # 2026-10-09, a fixed anchor so day buckets are stable


@pytest.fixture(autouse=True)
def _isolated_sources(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Point every aux source at an empty tmp directory."""
    claude = tmp_path / "claude-home"
    monkeypatch.setattr(aux, "AUTOPSY", claude / "autopsy.jsonl")
    monkeypatch.setattr(aux, "PROMPT_HISTORY", claude / "history.jsonl")
    monkeypatch.setattr(aux, "TIME_CAP", claude / "time-cap.jsonl")
    monkeypatch.setattr(ab, "LOG", claude / "agent-ab.jsonl")
    monkeypatch.setattr(context_files, "CLAUDE_DIR", claude)
    monkeypatch.setattr(context_files, "SRC_DIR", claude / "src")


def iso(offset: float) -> str:
    """ISO timestamp ``offset`` seconds after :data:`BASE`."""
    return datetime.fromtimestamp(BASE + offset, tz=UTC).isoformat()


def prompt(text: str, at: float, **extra: object) -> dict[str, Any]:
    """A typed user prompt."""
    return {
        "type": "user",
        "timestamp": iso(at),
        "cwd": "/repo",
        "message": {"role": "user", "content": text},
        **extra,
    }


def assistant(
    mid: str,
    at: float,
    *,
    output: int = 1000,
    model: str = "claude-opus-5-5",
    blocks: list[dict[str, Any]] | None = None,
    context: int = 0,
    **usage: object,
) -> dict[str, Any]:
    """One assistant record; ``context`` becomes cache-read tokens.

    ``usage`` adds raw usage fields, e.g. a cache-write split.
    """
    return {
        "type": "assistant",
        "timestamp": iso(at),
        "message": {
            "id": mid,
            "model": model,
            "usage": {
                "output_tokens": output,
                "cache_read_input_tokens": context,
                **usage,
            },
            "content": blocks or [{"type": "text", "text": "ok"}],
        },
    }


def use(tid: str, name: str, **tool_input: object) -> dict[str, Any]:
    """A ``tool_use`` content block."""
    return {"type": "tool_use", "id": tid, "name": name, "input": tool_input}


def result(
    tid: str, at: float, text: str = "x" * 40, **extra: object
) -> dict[str, Any]:
    """A user record carrying one ``tool_result``."""
    return {
        "type": "user",
        "timestamp": iso(at),
        "message": {
            "role": "user",
            "content": [{"type": "tool_result", "tool_use_id": tid, "content": text}],
        },
        **extra,
    }


def write(path: Path, records: list[dict[str, Any]]) -> Path:
    """Write records as JSONL, creating parent directories."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    return path


def usd_opus_output(tokens: int) -> float:
    """List price of ``tokens`` Opus 5.5 output tokens (USD 20 / MTok)."""
    return tokens * 20 / 1_000_000


def attach(at: float, **attachment: object) -> dict[str, Any]:
    """An ``attachment`` record."""
    return {"type": "attachment", "timestamp": iso(at), "attachment": attachment}


def walk_detail(tmp_path: Path, records: list[dict[str, Any]]) -> DetailRows:
    """Walk one main-session file and return its detail rows."""
    path = write(tmp_path / "proj" / "s.jsonl", records)
    return walk.walk_file(path, tmp_path).rows.detail
