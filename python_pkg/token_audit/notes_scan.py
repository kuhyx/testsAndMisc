"""Per-session facts the note join needs, read from every main transcript.

Only typed user prompts and assistant tool_use blocks are read; tool results
are never evidence (a session that reads BACKLOG.md names dozens of ids).
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import TYPE_CHECKING, Any

from python_pkg.token_audit import parse, records

if TYPE_CHECKING:
    from pathlib import Path

CLAIM = re.compile(r"note_claim\.sh\s+[\"']?([0-9A-Fa-f][0-9A-Fa-f-]{7,35})")
IMAGE = re.compile(r"todo-images/([0-9a-f]{8}-[0-9a-f-]{27})/")
HANDOFF_PROMPT = re.compile(r"^\s*(?:implement|continue)\s+(\S+)", re.IGNORECASE)
HANDOFF_DIR = ".claude/handoff/"
_WRAPPER = re.compile(
    r"<(system-reminder|command-[\w-]+|local-command[\w-]*)[^>]*>.*?</\1>", re.DOTALL
)
_PASTE_TAG = re.compile(r"</?pasted_content[^>]*>")
_BASH_CREATE = re.compile(r"(?:(?<![>&\d])>(?!>)|\btee\s+(?!-a))\s*[\"']?(\S+)")
_SKIP_PREFIX = ("Caveat:",)


@dataclass
class Facts:
    """What one main session contributes to the join."""

    session_id: str
    path: Path
    start: float = 0.0
    first_prompt: str = ""
    handoff: str | None = None
    claims: list[str] = field(default_factory=list)
    images: list[str] = field(default_factory=list)
    creates: dict[str, float] = field(default_factory=dict)


def handoff_rel(raw: str) -> str | None:
    """The path below ``~/.claude/handoff/``, or ``None`` if not under it."""
    _, sep, rel = raw.strip("\"'`").partition(HANDOFF_DIR)
    return rel.rstrip(".,;)") or None if sep else None


def prompt_text(record: dict[str, Any]) -> str | None:
    """Typed prompt text, wrappers removed; ``None`` for anything else."""
    if record.get("type") != "user" or record.get("isSidechain"):
        return None
    if record.get("isMeta"):
        return None
    content = (record.get("message") or {}).get("content")
    if isinstance(content, list):
        if any(b.get("type") == "tool_result" for b in content if isinstance(b, dict)):
            return None
        content = "\n".join(
            str(b.get("text") or "")
            for b in content
            if isinstance(b, dict) and b.get("type") == "text"
        )
    if not isinstance(content, str):
        return None
    text = _PASTE_TAG.sub("", _WRAPPER.sub("", content)).strip()
    return "" if text.startswith(_SKIP_PREFIX) else text


def _created_paths(name: str, tool_input: dict[str, Any]) -> list[str]:
    if name == "Write":
        path = tool_input.get("file_path")
        return [path] if isinstance(path, str) else []
    command = tool_input.get("command")
    if name != "Bash" or not isinstance(command, str) or HANDOFF_DIR not in command:
        return []
    return _BASH_CREATE.findall(command)


def _tool_uses(record: dict[str, Any]) -> list[dict[str, Any]]:
    if record.get("type") != "assistant":
        return []
    content = (record.get("message") or {}).get("content")
    blocks = content if isinstance(content, list) else []
    return [b for b in blocks if isinstance(b, dict) and b.get("type") == "tool_use"]


def _use(facts: Facts, record: dict[str, Any], *, main: bool) -> None:
    stamp = records.timestamp(record) or 0.0
    for block in _tool_uses(record):
        tool_input = block.get("input") if isinstance(block.get("input"), dict) else {}
        name = str(block.get("name"))
        if main and name == "Bash":
            facts.claims += CLAIM.findall(str(tool_input.get("command") or ""))
        for raw in _created_paths(name, tool_input):
            rel = handoff_rel(raw)
            if rel is not None and rel not in facts.creates:
                facts.creates[rel] = stamp


def _prompt(facts: Facts, record: dict[str, Any]) -> None:
    text = prompt_text(record)
    if not text:
        return
    facts.images += [i for i in IMAGE.findall(text) if i not in facts.images]
    if not facts.first_prompt:
        facts.first_prompt = text
        match = HANDOFF_PROMPT.match(text)
        facts.handoff = handoff_rel(match.group(1)) if match else None


def _wanted(line: str) -> bool:
    if '"tool_use"' in line:
        return "note_claim" in line or HANDOFF_DIR in line
    return '"type":"user"' in line and '"tool_result"' not in line


def scan(path: Path, *, main: bool = True) -> Facts:
    """Read one transcript's prompts, claims and handoff-file creations."""
    facts = Facts(session_id=path.stem, path=path)
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not facts.start and '"timestamp"' in line:
                facts.start = records.timestamp(parse.load_line(line) or {}) or 0.0
            if not _wanted(line):
                continue
            record = parse.load_line(line) or {}
            _use(facts, record, main=main)
            if main:
                _prompt(facts, record)
    return facts


def scan_root(root: Path) -> dict[str, Facts]:
    """Facts per main session; subagent creations fold into their parent."""
    found = {p.stem: scan(p) for p in sorted(root.glob("*/*.jsonl"))}
    for sub in sorted(root.glob("*/*/subagents/agent-*.jsonl")):
        parent = found.get(sub.parent.parent.name)
        if parent is None:
            continue
        for rel, stamp in scan(sub, main=False).creates.items():
            parent.creates[rel] = min(stamp, parent.creates.get(rel, stamp))
    return found
