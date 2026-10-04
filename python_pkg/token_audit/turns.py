"""Build a :class:`Turn` from one assistant transcript record.

Split out of :mod:`parse` to keep both under the file-length cap; this half is
the pure record -> turn conversion, with no I/O and no ordering concerns.
"""

from __future__ import annotations

from typing import Any

from python_pkg.token_audit import records
from python_pkg.token_audit.model import Turn


def usage_of(record: dict[str, Any]) -> tuple[dict[str, Any], dict[str, int]] | None:
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
    flat = {k: v for k, v in usage.items() if isinstance(v, int)}
    return message, flat | records.cache_split(usage)


def _model(message: dict[str, Any]) -> str:
    """Return the model id that served a record, or a placeholder.

    Only ever called after :func:`_usage` has confirmed the message is a dict,
    so it takes the message itself rather than re-checking the record.
    """
    model = message.get("model")
    return model if isinstance(model, str) else "unknown"


def build_turn(
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
        timestamp=records.timestamp(record) or 0.0,
    )
