"""Builders for fixture transcripts, BACKLOG files and Firebase dumps."""

from __future__ import annotations

import gzip
import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

NOTE_A = "aaaaaaaa-1111-4111-8111-000000000001"
NOTE_B = "bbbbbbbb-2222-4222-8222-000000000002"
NOTE_C = "cccccccc-3333-4333-8333-000000000003"
NOTE_D = "dddddddd-4444-4444-8444-000000000004"

BODY_A = (
    "diet guard meal times picker\n\n"
    "allow user to pick meal hours in intervals of fifteen minutes "
    "instead of typing them, remember the last chosen catering option"
)
BODY_B = (
    "spellcode audio from first frame\n\n"
    "play hub music and ambience immediately when the godot game opens, "
    "no silent splash screen, crossfade between rooms"
)
BODY_C = "book guard volume buttons\n\nvolume keys turn reader pages forward backward"
BODY_D = "horror game"


def backlog(path: Path, notes: list[tuple[str, str, str, str]] | None = None) -> Path:
    """Write a BACKLOG.md with ``(id, status, updated, body)`` notes."""
    notes = notes or [
        (NOTE_A, "done", "2026-10-20T10:00:00.000", BODY_A),
        (NOTE_B, "abandoned", "2026-10-21T10:00:00.000", BODY_B),
        (NOTE_C, "todo", "2026-10-22T10:00:00.000", BODY_C),
        (NOTE_D, "done", "2026-09-01T10:00:00.000", BODY_D),
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    parts = ["<!-- todo-backlog v1 -->", ""]
    for note_id, status, updated, body in notes:
        parts += [
            f'<!-- @note id="{note_id}" priority="high" status="{status}" '
            f'created="2026-09-01T00:00:00.000" updated="{updated}" -->',
            body,
            "",
        ]
    path.write_text("\n".join(parts), encoding="utf-8")
    return path


def dump(directory: Path, stamp: str, statuses: dict[str, tuple[int, str]]) -> Path:
    """Write one ``kuhy-syncs-<stamp>.json.gz`` with ``id -> (status, hlc)``."""
    directory.mkdir(parents=True, exist_ok=True)
    device = {
        note_id: {
            "id": note_id,
            "fields": {"status": [status, f"{hlc}-0000-dev1"]},
            "deleted": False,
            "deleted_hlc": None,
        }
        for note_id, (status, hlc) in statuses.items()
    }
    data = {"todo-sync": {"notes": {"dev1~2Ejson": json.dumps(device)}}}
    path = directory / f"kuhy-syncs-{stamp}.json.gz"
    path.write_bytes(gzip.compress(json.dumps(data).encode()))
    return path


def prompt(text: str, stamp: str = "2026-10-20T09:00:00Z") -> dict[str, Any]:
    """A typed user prompt record."""
    return {
        "type": "user",
        "timestamp": stamp,
        "cwd": "/home/kuhy/demo",
        "message": {"role": "user", "content": text},
    }


def tool_use(
    name: str,
    tool_input: dict[str, Any],
    stamp: str = "2026-10-20T09:01:00Z",
    msg: str = "m1",
    usd_tokens: int = 1000,
) -> dict[str, Any]:
    """An assistant record carrying one tool_use and a usage block."""
    return {
        "type": "assistant",
        "timestamp": stamp,
        "message": {
            "id": msg,
            "model": "claude-opus-5-5",
            "usage": {"input_tokens": 0, "output_tokens": usd_tokens},
            "content": [
                {
                    "type": "tool_use",
                    "id": f"t-{msg}",
                    "name": name,
                    "input": tool_input,
                }
            ],
        },
    }


def tool_result(text: str, msg: str = "m1") -> dict[str, Any]:
    """A tool_result record (not a prompt)."""
    return {
        "type": "user",
        "timestamp": "2026-10-20T09:02:00Z",
        "message": {
            "content": [
                {"type": "tool_result", "tool_use_id": f"t-{msg}", "content": text}
            ]
        },
    }


def _write(path: Path, records: list[dict[str, Any]]) -> None:
    lines = (json.dumps(r, separators=(",", ":")) for r in records)
    path.write_text("\n".join(lines), encoding="utf-8")


def transcript(
    root: Path, session: str, records: list[dict[str, Any]], slug: str = "proj"
) -> Path:
    """Write ``<root>/<slug>/<session>.jsonl``."""
    project = root / slug
    project.mkdir(parents=True, exist_ok=True)
    path = project / f"{session}.jsonl"
    path.write_text(
        "\n".join(json.dumps(r, separators=(",", ":")) for r in records),
        encoding="utf-8",
    )
    return path


def subagent(
    root: Path, session: str, agent: str, records: list[dict[str, Any]]
) -> Path:
    """Write ``<root>/proj/<session>/subagents/agent-<agent>.jsonl``."""
    directory = root / "proj" / session / "subagents"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"agent-{agent}.jsonl"
    path.write_text(
        "\n".join(json.dumps(r, separators=(",", ":")) for r in records),
        encoding="utf-8",
    )
    return path
