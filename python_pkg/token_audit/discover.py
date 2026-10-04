"""Find transcript files and read the per-file metadata around them.

Two layouts hold billed turns:

* ``<root>/<project-slug>/<session-id>.jsonl`` -- the main conversation.
* ``<root>/<project-slug>/<session-id>/subagents/agent-<id>.jsonl`` -- one per
  ``Agent`` call, with a sibling ``agent-<id>.meta.json`` naming the agentType
  and description. Before 2026-10-04 the audit globbed only the first layout
  and reported subagents at 0.0% while they were 35% of real spend.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

PATTERNS: tuple[str, ...] = ("*/*.jsonl", "*/*/subagents/agent-*.jsonl")


def find_transcripts(root: Path, since: float) -> list[Path]:
    """Return transcripts that may hold records after ``since``, newest first.

    A file last written before ``since`` cannot hold an in-window record, so
    mtime prunes those. There is deliberately no mtime upper bound: a file
    still being appended to after the window closed holds in-window records
    too, and the per-record timestamp filter in :func:`parse.iter_events`
    trims whatever falls outside.
    """
    found: list[tuple[float, Path]] = []
    for pattern in PATTERNS:
        for path in sorted(root.glob(pattern)):
            mtime = path.stat().st_mtime
            if mtime >= since:
                found.append((mtime, path))
    return [path for _, path in sorted(found, reverse=True)]


def _record(line: str) -> dict[str, Any] | None:
    """Parse one JSON object, or ``None``."""
    try:
        loaded = json.loads(line)
    except ValueError:
        return None
    return loaded if isinstance(loaded, dict) else None


def first_cwd(path: Path) -> str | None:
    """Return the working directory a transcript was recorded in."""
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            record = _record(line)
            if record is not None:
                cwd = record.get("cwd")
                if isinstance(cwd, str):
                    return cwd
    return None


def agent_meta(path: Path) -> dict[str, Any]:
    """Return a subagent transcript's sibling ``.meta.json``, or ``{}``."""
    meta = path.with_suffix(".meta.json")
    if not meta.exists():
        return {}
    return _record(meta.read_text(encoding="utf-8", errors="replace")) or {}
