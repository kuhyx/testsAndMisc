"""Read context marks out of the records that are not the conversation.

Hooks write ``attachment`` records: ``hook_success`` (every run, with its
command and duration; SessionStart / UserPromptSubmit stdout is injected as
context), ``hook_additional_context`` (injected text, without the command --
joined back to its run by :mod:`hook_join`), ``hook_blocking_error`` (a block
or a Stop-hook bounce) and ``hook_system_message`` (shown to the user only).
Other attachment types in :data:`INJECTED` are rendered into the prompt;
the rest (``prompt_snapshot``, ``environment`` ...) only record what was sent.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import TYPE_CHECKING, Any

from python_pkg.token_audit import parse
from python_pkg.token_dashboard import blocks, classify

if TYPE_CHECKING:
    from collections.abc import Iterator

CHARS = parse.CHARS_PER_TOKEN
# Marks that never sit in the model's context, so carry nothing.
NOT_IN_CONTEXT = frozenset({"hook_msg", "compaction", "api_error", "interrupt"})
# Hook events whose plain stdout Claude Code adds to the context.
INJECTING = frozenset({"SessionStart", "UserPromptSubmit"})
INJECTED = frozenset(
    {
        "nested_memory",
        "edited_text_file",
        "total_tokens_reminder",
        "skill_listing",
        "deferred_tools_delta",
        "mcp_instructions_delta",
        "agent_listing_delta",
        "queued_command",
        "task_reminder",
        "silent_turn_reminder",
        "file",
        "todo",
        "command_permissions",
    }
)
_SCRIPTS = (".sh", ".py", ".js", ".ts", ".mjs")
SNIPPET = 40


@dataclass(frozen=True)
class Found:
    """One mark read from a record, before it becomes a row.

    ``key`` (tool-use id, hook name) and ``text`` only matter to hook runs
    and hook context, which :mod:`hook_join` pairs up.
    """

    kind: str
    name: str
    detail: str = ""
    count: int = 1
    tokens: int = 0
    extra: int = 0
    duration_ms: int = 0
    key: tuple[str, str] = ("", "")
    text: str = ""


def short_command(command: str) -> str:
    """A hook command's script name, or its first 40 characters."""
    words = command.split()
    scripts = [w for w in words if w.endswith(_SCRIPTS)]
    if scripts:
        return scripts[0].rsplit("/", 1)[-1]
    return " ".join(words)[:SNIPPET]


def _int(value: object) -> int:
    """A number that may arrive as a string; 0 when it is neither."""
    try:
        return int(float(str(value)))
    except ValueError:
        return 0


def split_images(content: object) -> tuple[int, str]:
    """Image block count and the JSON text of everything else."""
    if not isinstance(content, list):
        return 0, "" if content is None else json.dumps(content)
    images = [b for b in content if isinstance(b, dict) and b.get("type") == "image"]
    rest = [b for b in content if b not in images]
    return len(images), json.dumps(rest)


def _tokens(text: object) -> int:
    """Estimated tokens of a text value."""
    return len(str(text or "")) // CHARS


def _hook(att: dict[str, Any]) -> Iterator[Found]:
    """Marks of one hook attachment."""
    kind = att.get("type")
    name = str(att.get("hookName") or "")
    key = (str(att.get("toolUseID") or ""), name)
    content = att.get("content")
    if kind == "hook_success":
        text = str(content or "")
        injected = att.get("hookEvent") in INJECTING
        injected = injected and not text.lstrip().startswith("{")
        yield Found(
            "hook_run",
            name,
            detail=short_command(str(att.get("command") or "")),
            duration_ms=_int(att.get("durationMs")),
            tokens=_tokens(text) if injected else 0,
            key=key,
            text=str(att.get("stdout") or ""),
        )
    elif kind == "hook_additional_context":
        for item in content if isinstance(content, list) else [content]:
            text = str(item or "")
            yield Found("hook_context", name, tokens=_tokens(text), key=key, text=text)
    elif kind == "hook_blocking_error":
        raw = att.get("blockingError")
        error = raw if isinstance(raw, dict) else {"blockingError": raw}
        command = short_command(str(error.get("command") or ""))
        yield Found(
            "hook_block", name, detail=command, tokens=_tokens(error["blockingError"])
        )
    elif kind == "hook_non_blocking_error":
        yield Found("hook_error", name, tokens=_tokens(content))
    elif kind == "hook_system_message":
        yield Found("hook_msg", name)


def _attachment(att: dict[str, Any]) -> Iterator[Found]:
    """Marks of one attachment record."""
    kind = str(att.get("type") or "")
    if kind.startswith("hook_"):
        yield from _hook(att)
    elif kind in INJECTED:
        rest = {k: v for k, v in att.items() if k != "type"}
        path = str(att.get("path") or "")[: classify.TARGET_CHARS]
        yield Found("attach", kind, detail=path, tokens=_tokens(json.dumps(rest)))


def _user(rec: dict[str, Any]) -> Iterator[Found]:
    """Interruptions and pasted images."""
    message = rec.get("message")
    content = message.get("content") if isinstance(message, dict) else None
    if blocks.text_of(content).startswith("[Request interrupted"):
        yield Found("interrupt", "user")
    images, _ = split_images(content)
    if images:
        yield Found("image", "user", count=images, tokens=images * parse.IMAGE_TOKENS)


def of_record(rec: dict[str, Any]) -> list[Found]:
    """Every mark one non-assistant record carries."""
    kind = rec.get("type")
    att = rec.get("attachment")
    if kind == "attachment" and isinstance(att, dict):
        return list(_attachment(att))
    if kind == "system" and rec.get("subtype") == "compact_boundary":
        meta = rec.get("compactMetadata")
        meta = meta if isinstance(meta, dict) else {}
        found = Found(
            "compaction",
            str(meta.get("trigger") or "manual"),
            tokens=_int(meta.get("preTokens")),
            extra=_int(meta.get("postTokens")),
            duration_ms=_int(meta.get("durationMs")),
        )
        return [found]
    if kind == "user":
        return list(_user(rec))
    return []
