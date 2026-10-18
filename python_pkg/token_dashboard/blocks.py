"""Pure readers for individual transcript records and content blocks.

Split from :mod:`walk` so the record-level rules (what counts as a typed
prompt, how a status tag or a commit hash is recognised) are testable without a
file and the walker stays under the file-length cap.
"""

from __future__ import annotations

import os
from pathlib import Path
import re
from typing import Any

from python_pkg.token_audit.discover import WRAPPER

PROMPT_CHARS = 120
LEVER_HEADING = "Candidate levers (rule-based)"
# kuhy's convention: every final reply ends on one of these status tags.
TAG = re.compile(r"^\W*(DONE|RUNNING|QUESTION|NEEDS ACTION)\W*:", re.MULTILINE)
COMMAND = re.compile(r"<command-name>\s*(\S+?)\s*</command-name>")
# `git commit` prints `[branch sha] subject`, also through finish_auto.sh.
COMMIT_LINE = re.compile(
    r"^\[[^\]\s]+(?: \(root-commit\))? ([0-9a-f]{7,40})\]", re.MULTILINE
)
REPO_HINT = re.compile(r"(?:git\s+-C|\bcd)\s+(\"[^\"]+\"|'[^']+'|[^\s;&|]+)")
_SKIP_PREFIXES = ("[Request interrupted", "Caveat:")


def text_of(content: object) -> str:
    """Flatten a message/tool-result ``content`` into plain text."""
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    parts = [
        str(block.get("text") or "")
        for block in content
        if isinstance(block, dict) and block.get("type") == "text"
    ]
    return "\n".join(parts)


def prompt_text(record: dict[str, Any]) -> str | None:
    """The typed text of a real user prompt, or ``None`` for anything else.

    Excludes tool results, ``isMeta`` / compact-summary records, interrupts,
    and harness-injected ``<tag>`` blocks. A slash command keeps its name.
    """
    if record.get("type") != "user" or record.get("isMeta"):
        return None
    if record.get("isCompactSummary") or record.get("isVisibleInTranscriptOnly"):
        return None
    message = record.get("message")
    content = message.get("content") if isinstance(message, dict) else None
    if isinstance(content, list) and any(
        isinstance(b, dict) and b.get("type") == "tool_result" for b in content
    ):
        return None
    raw = text_of(content)
    command = COMMAND.search(raw)
    text = WRAPPER.sub("", raw).strip()
    if command is not None and not text:
        text = command.group(1)
    if not text or text.startswith(_SKIP_PREFIXES):
        return None
    return " ".join(text.split())[:PROMPT_CHARS]


def final_tag(text: str) -> str | None:
    """The last status tag in a reply, or ``None`` when it carries none."""
    found = TAG.findall(text)
    return found[-1] if found else None


def commit_shas(text: str) -> list[str]:
    """Commit hashes printed by ``git commit`` in a tool result."""
    return COMMIT_LINE.findall(text)


def repo_hint(command: str, cwd: str | None) -> str:
    """The repository a commit command ran in: ``-C``/``cd`` target, else cwd."""
    match = REPO_HINT.search(command)
    target = match.group(1).strip("\"'") if match else (cwd or "")
    if not target:
        return ""
    path = Path(target).expanduser()
    if cwd and not path.is_absolute():
        path = Path(cwd) / path
    return os.path.normpath(path)


def lever_table(text: str) -> str | None:
    """The markdown table following the candidate-levers heading, if any."""
    at = text.find(LEVER_HEADING)
    if at < 0:
        return None
    rows: list[str] = []
    for line in text[at:].splitlines()[1:]:
        if line.startswith("|"):
            rows.append(line)
        elif rows:
            break
    return "\n".join(rows) if rows else None
