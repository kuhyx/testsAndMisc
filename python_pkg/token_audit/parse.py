"""Read Claude Code transcripts into :class:`Session` objects.

Transcripts are JSONL under ``~/.claude/projects/<slug>/<session-id>.jsonl``,
one JSON object per line, appended live. Three properties of that format drive
the design here:

1. **Lines can be malformed.** A transcript being written while it is read can
   end in a partial line, and older sessions contain records this package does
   not model. Every line is therefore parsed defensively and skipped on error;
   losing one line is always better than aborting a weekly report.
2. **A tool call and its result are in different messages.** ``tool_use`` blocks
   carry the name and input, ``tool_result`` blocks carry the payload and only a
   ``tool_use_id`` back-reference. Attributing result size to the right tool
   requires holding an id map for the length of the file.
3. **Order matters.** The image-cost model needs to know how many turns followed
   each image, so :func:`iter_events` preserves the interleaving rather than
   returning separate lists.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from python_pkg.token_audit.model import IMAGE_SUFFIXES, Session, ToolCall, Turn

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

# Divisor turning rendered characters into an approximate token count. Four is
# the usual English-text rule of thumb and is only ever used for ranking tools,
# never for the reconciled totals.
CHARS_PER_TOKEN = 4

# Median billed size of one screenshot, measured from real transcripts by
# isolating turns whose only new content was a single image (n=484, median
# 2,566, p90 2,692). Anthropic bills images by pixel area, so a constant is a
# far better estimate than the base64 payload length, which is ~20x too high.
# Halving a screenshot's dimensions cuts this roughly fourfold.
IMAGE_TOKENS = 2566


def _load_line(line: str) -> dict[str, Any] | None:
    """Parse one JSONL line, returning ``None`` if it is not a usable record."""
    try:
        record = json.loads(line)
    except (ValueError, UnicodeDecodeError):
        return None
    return record if isinstance(record, dict) else None


def _blocks(record: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the content blocks of a record's message, if it has any."""
    message = record.get("message")
    if not isinstance(message, dict):
        return []
    content = message.get("content")
    if not isinstance(content, list):
        return []
    return [block for block in content if isinstance(block, dict)]


def _usage(record: dict[str, Any]) -> tuple[dict[str, Any], dict[str, int]] | None:
    """Return an assistant record's message and its integer usage fields.

    The message is returned alongside the usage block so callers that need both
    (the model id lives on the message) never have to re-validate its type.
    """
    message = record.get("message")
    if not isinstance(message, dict):
        return None
    usage = message.get("usage")
    if not isinstance(usage, dict):
        return None
    return message, {k: v for k, v in usage.items() if isinstance(v, int)}


def _model(message: dict[str, Any]) -> str:
    """Return the model id that served a record, or a placeholder.

    Only ever called after :func:`_usage` has confirmed the message is a dict,
    so it takes the message itself rather than re-checking the record.
    """
    model = message.get("model")
    return model if isinstance(model, str) else "unknown"


def _result_tokens(block: dict[str, Any], *, is_image: bool = False) -> int:
    """Estimate how many tokens a tool result occupied in context.

    Text is charged by length, but an **image is not**. An image arrives as a
    base64 blob whose character count has nothing to do with its billed size —
    Anthropic charges by pixel area. Measuring images by payload length
    overstates them by roughly 20x (a 240KB PNG looks like ~82k tokens against
    a real cost near 2.5k), which is enough to make screenshots look like the
    dominant cost driver when they are not. Validated against real transcripts
    by isolating turns whose only new content was one image: the context grew
    ~1.6-3k tokens, never the tens of thousands the payload length implied.
    """
    content = block.get("content")
    if content is None:
        return 0
    if is_image:
        return IMAGE_TOKENS
    return len(json.dumps(content)) // CHARS_PER_TOKEN


def iter_events(path: Path) -> Iterator[tuple[str, object]]:
    """Yield ``("turn", Turn)`` and ``("tool", ToolCall)`` in transcript order.

    Emitting a single ordered stream — rather than two lists — is what lets
    :mod:`imagecost` count how many turns each image survived for.
    """
    pending: dict[str, dict[str, Any]] = {}
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            record = _load_line(line)
            if record is None:
                continue
            for block in _blocks(record):
                kind = block.get("type")
                if kind == "tool_use":
                    call_id = block.get("id")
                    if isinstance(call_id, str):
                        pending[call_id] = block
                elif kind == "tool_result":
                    call = _pair_result(block, pending)
                    if call is not None:
                        yield "tool", call
            found = _usage(record)
            if found is not None:
                message, usage = found
                yield "turn", _build_turn(record, message, usage)


def _pair_result(
    block: dict[str, Any],
    pending: dict[str, dict[str, Any]],
) -> ToolCall | None:
    """Join a ``tool_result`` back to the ``tool_use`` that produced it."""
    use = pending.pop(block.get("tool_use_id", ""), None)
    if use is None:
        return None
    tool_input = use.get("input")
    tool_input = tool_input if isinstance(tool_input, dict) else {}
    path = tool_input.get("file_path")
    skill = tool_input.get("skill")
    call_path = path if isinstance(path, str) else None
    return ToolCall(
        name=str(use.get("name") or "unknown"),
        result_tokens=_result_tokens(block, is_image=_looks_like_image(call_path)),
        path=call_path,
        skill=skill if isinstance(skill, str) else None,
    )


def _looks_like_image(path: str | None) -> bool:
    """Whether a tool-result path refers to an image, by extension."""
    if path is None:
        return False
    dot = path.rfind(".")
    return dot != -1 and path[dot:].lower() in IMAGE_SUFFIXES


def _build_turn(
    record: dict[str, Any],
    message: dict[str, Any],
    usage: dict[str, int],
) -> Turn:
    """Build a :class:`Turn` from an assistant record's usage block."""
    context = usage.get("cache_read_input_tokens", 0) + usage.get(
        "cache_creation_input_tokens",
        0,
    )
    message_id = message.get("id")
    content = message.get("content")
    tool_calls = (
        sum(
            1
            for block in content
            if isinstance(block, dict) and block.get("type") == "tool_use"
        )
        if isinstance(content, list)
        else 0
    )
    return Turn(
        usage=usage,
        context=context,
        model=_model(message),
        is_sidechain=bool(record.get("isSidechain")),
        message_id=message_id if isinstance(message_id, str) else "",
        tool_calls=tool_calls,
    )


def _first_cwd(path: Path) -> str | None:
    """Return the working directory a transcript was recorded in."""
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            record = _load_line(line)
            if record is not None:
                cwd = record.get("cwd")
                if isinstance(cwd, str):
                    return cwd
    return None


def load_session(path: Path) -> Session:
    """Read one transcript file into a :class:`Session`."""
    session = Session(session_id=path.stem, path=str(path), cwd=_first_cwd(path))
    for kind, event in iter_events(path):
        if kind == "turn" and isinstance(event, Turn):
            session.turns.append(event)
        elif isinstance(event, ToolCall):
            session.tools.append(event)
    return session


def find_transcripts(
    root: Path,
    since: float,
    until: float | None = None,
) -> list[Path]:
    """Return transcripts modified inside the window, newest first.

    Modification time is the selector because it is the only per-file timestamp
    available without opening the file, and a session's mtime is when it was
    last active — exactly the notion of "used this week" the report wants.
    """
    found: list[tuple[float, Path]] = []
    for path in sorted(root.glob("*/*.jsonl")):
        mtime = path.stat().st_mtime
        if mtime >= since and (until is None or mtime <= until):
            found.append((mtime, path))
    return [path for _, path in sorted(found, reverse=True)]
