"""Todo notes plus their done date: the status HLC in the first dump showing it.

The app keeps no done timestamp; the BACKLOG parse copies todo_mcp/_backlog.py.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
import gzip
import json
from pathlib import Path
import re
from typing import Any

STATUSES = ("todo", "inProgress", "done", "abandoned")
TERMINAL = frozenset({"done", "abandoned"})
_MARKER = re.compile(r"^<!--\s*@note\s+(.*?)\s*-->[ \t]*$", re.MULTILINE)
_ATTR = re.compile(r'(\w+)="([^"]*)"')
_HLC = re.compile(r"^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?)Z")
_DUMP_GLOB = "kuhy-syncs-*.json.gz"
_FIELD_LEN = 2


@dataclass(frozen=True)
class Note:
    """One backlog note; ``done_at`` is set only for done/abandoned notes."""

    id: str
    title: str
    body: str
    priority: str
    status: str
    updated: float | None
    done_at: float | None = None


def backlog_path() -> Path:
    """Where the app's Settings -> Export notes writes BACKLOG.md."""
    return Path.home() / "src" / "todo" / "BACKLOG.md"


def dumps_dir() -> Path:
    """Where the daily Firebase RTDB backups land."""
    return Path.home() / "data" / "cloud" / "firebase_backups"


def _local_time(raw: str | None) -> float | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw).timestamp()
    except ValueError:
        return None


def parse_backlog(text: str) -> list[Note]:
    """Every ``<!-- @note ... -->`` block in an exported BACKLOG.md."""
    markers = list(_MARKER.finditer(text))
    out: list[Note] = []
    for index, marker in enumerate(markers):
        attrs = dict(_ATTR.findall(marker.group(1)))
        end = markers[index + 1].start() if index + 1 < len(markers) else len(text)
        body = text[marker.end() : end].strip()
        status = attrs.get("status", "todo")
        out.append(
            Note(
                id=attrs.get("id", ""),
                title=body.splitlines()[0].lstrip("#").strip() if body else "",
                body=body,
                priority=attrs.get("priority", "medium"),
                status=status if status in STATUSES else "todo",
                updated=_local_time(attrs.get("updated")),
            )
        )
    return out


def hlc_time(hlc: object) -> float | None:
    """The wall-clock part of an HLC string (``<iso>Z-<counter>-<node>``)."""
    match = _HLC.match(hlc) if isinstance(hlc, str) else None
    if match is None:
        return None
    return datetime.fromisoformat(match.group(1)).replace(tzinfo=UTC).timestamp()


def _status_field(note: object) -> tuple[int, str] | None:
    if not isinstance(note, dict) or note.get("deleted"):
        return None
    field = (note.get("fields") or {}).get("status")
    if not isinstance(field, list) or len(field) != _FIELD_LEN:
        return None
    value, hlc = field
    return (value, hlc) if isinstance(value, int) and isinstance(hlc, str) else None


def merge_devices(devices: dict[str, Any]) -> dict[str, tuple[int, str]]:
    """Last-writer-wins status per note across the per-device documents."""
    merged: dict[str, tuple[int, str]] = {}
    for raw in devices.values():
        try:
            doc = json.loads(raw) if isinstance(raw, str) else raw
        except ValueError:
            continue
        for note_id, note in (doc if isinstance(doc, dict) else {}).items():
            found = _status_field(note)
            if found is not None and (
                note_id not in merged or found[1] > merged[note_id][1]
            ):
                merged[note_id] = found
    return merged


def _dump_statuses(path: Path) -> dict[str, tuple[int, str]]:
    try:
        data = json.loads(gzip.decompress(path.read_bytes()))
    except OSError, ValueError, EOFError:
        return {}
    devices = ((data or {}).get("todo-sync") or {}).get("notes") or {}
    return merge_devices(devices) if isinstance(devices, dict) else {}


def first_seen(directory: Path) -> dict[str, dict[str, float]]:
    """Per note and terminal status: its status HLC in the first dump showing it."""
    seen: dict[str, dict[str, float]] = {}
    for path in sorted(directory.glob(_DUMP_GLOB)) if directory.is_dir() else []:
        for note_id, (value, hlc) in _dump_statuses(path).items():
            status = STATUSES[value] if 0 <= value < len(STATUSES) else "todo"
            stamp = hlc_time(hlc)
            if status in TERMINAL and stamp is not None:
                seen.setdefault(note_id, {}).setdefault(status, stamp)
    return seen


def _dated(note: Note, seen: dict[str, dict[str, float]]) -> Note:
    if note.status not in TERMINAL:
        return note
    return replace(note, done_at=seen.get(note.id, {}).get(note.status, note.updated))


def load_notes(backlog: Path, dumps: Path) -> list[Note]:
    """BACKLOG notes with ``done_at`` filled for done/abandoned ones."""
    seen = first_seen(dumps)
    text = backlog.read_text(encoding="utf-8")
    return [_dated(note, seen) for note in parse_backlog(text)]
