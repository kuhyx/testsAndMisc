"""Find transcript files and read the per-file metadata around them.

Two layouts hold billed turns:

* ``<root>/<project-slug>/<session-id>.jsonl`` -- the main conversation.
* ``<root>/<project-slug>/<session-id>/subagents/agent-<id>.jsonl`` -- one per
  ``Agent`` call, with a sibling ``agent-<id>.meta.json`` naming the agentType
  and description. Before 2026-10-04 the audit globbed only the first layout
  and reported subagents at 0.0% while they were 35% of real spend.

A background agent outlives ``/clear``: the rest of its transcript lands in the
*new* session's ``subagents/`` under the same ``agent-<id>`` name, starting
mid-conversation and with no ``.meta.json`` (or one without a description).
:func:`agent_meta` borrows the label from the spawning session's copy; on
2026-10-10 that was all 14 unlabelled files, 5.2% of a week's spend.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

PATTERNS: tuple[str, ...] = ("*/*.jsonl", "*/*/subagents/agent-*.jsonl")

# Harness-injected ``<tag>...</tag>`` blocks (``<fork-boilerplate>``,
# ``<system-reminder>``): identical across agents, so never a useful label.
WRAPPER = re.compile(r"<([\w-]+)[^>]*>.*?</\1>", re.DOTALL)


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


def _meta_file(meta: Path) -> dict[str, Any]:
    """Read one ``.meta.json``, ``{}`` when missing or unreadable."""
    if not meta.exists():
        return {}
    return _record(meta.read_text(encoding="utf-8", errors="replace")) or {}


def agent_meta(path: Path) -> dict[str, Any]:
    """Return a subagent transcript's metadata, or ``{}``.

    The sibling ``.meta.json`` wins; any field it lacks is filled from the same
    agent's meta in another session directory (see the module docstring).
    """
    own = _meta_file(path.with_suffix(".meta.json"))
    if own.get("description"):
        return own
    projects = path.parents[3]
    for other in sorted(projects.glob(f"*/*/subagents/{path.stem}.meta.json")):
        borrowed = _meta_file(other)
        if borrowed.get("description"):
            return {**borrowed, **{k: v for k, v in own.items() if v}}
    return own


def _prompt_text(record: dict[str, Any]) -> str | None:
    """The typed text of a ``user`` record, ignoring tool results."""
    if record.get("type") != "user":
        return None
    message = record.get("message")
    content = message.get("content") if isinstance(message, dict) else None
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                return str(block.get("text") or "")
    return None


def first_prompt(path: Path, limit: int = 60) -> str:
    """First non-blank line of a transcript's first user prompt, truncated.

    The label of last resort for a subagent nobody described: better than
    ``?`` because it names the work, and an empty result means none exists.
    """
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            record = _record(line)
            text = _prompt_text(record) if record is not None else None
            text = WRAPPER.sub("", text or "")
            lines = [part.strip() for part in text.splitlines()]
            first = next((part for part in lines if part), "")
            if first:
                return first if len(first) <= limit else first[: limit - 1] + "…"
    return ""
