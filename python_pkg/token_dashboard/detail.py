"""Collect the detail rows (calls, marks, turn facts) during a file walk.

The walker feeds every record, tool call, tool result and priced turn here;
:meth:`Detail.finish` settles creation and carry cost on each row. Marks come
from what Claude Code writes next to the conversation (see :mod:`marks`).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from python_pkg.token_audit import parse, records
from python_pkg.token_audit.pricing import WRITE_1H, WRITE_5M
from python_pkg.token_dashboard import blocks, carry, classify, hook_join, marks
from python_pkg.token_dashboard.detail_rows import (
    CallRow,
    DetailRows,
    MarkRow,
    TurnDetail,
    Where,
)

if TYPE_CHECKING:
    from python_pkg.token_audit.model import Turn
    from python_pkg.token_audit.pricing import PriceBook

CHARS = parse.CHARS_PER_TOKEN


def write_multiplier(usage: dict[str, int]) -> float:
    """Average cache-write price of one call, as a multiple of input."""
    total = usage.get("cache_creation_input_tokens", 0)
    if not total:
        return WRITE_5M
    one_hour = min(usage.get(records.CACHE_1H, 0), total)
    return (one_hour * WRITE_1H + (total - one_hour) * WRITE_5M) / total


def _message(rec: dict[str, Any]) -> dict[str, Any]:
    """A record's ``message`` dict, empty when absent."""
    message = rec.get("message")
    return message if isinstance(message, dict) else {}


class _Output:
    """Visible output of one API message, accumulated over its records."""

    def __init__(self, latency: float) -> None:
        """Start empty; ``latency`` is the gap before the first record."""
        self.latency = latency
        self.text = 0
        self.tool = 0
        self.thinking = False

    def add(self, block: dict[str, Any]) -> None:
        """Count one content block."""
        kind = block.get("type")
        if kind == "text":
            self.text += len(str(block.get("text") or ""))
        elif kind == "tool_use":
            self.tool += len(json.dumps(block.get("input") or {}))
        elif kind in {"thinking", "redacted_thinking"}:
            self.thinking = True

    def split(self, output: int) -> tuple[int, int, int]:
        """``(text, tool, thinking)`` tokens summing to ``output``.

        Visible blocks are estimated by length; billed output left over is
        thinking (whose text Claude Code does not keep). With no thinking
        block, or more visible text than output, the visible estimates are
        scaled to the billed total instead.
        """
        text, tool = self.text // CHARS, self.tool // CHARS
        visible = text + tool
        if not visible:
            return (0, 0, output) if self.thinking else (output, 0, 0)
        if visible > output or not self.thinking:
            text = round(output * text / visible)
            return text, output - text, 0
        return text, tool, output - visible


class Detail:
    """Detail state for one file."""

    def __init__(self) -> None:
        """Nothing seen yet."""
        self.rows = DetailRows()
        self.tracker = carry.Tracker()
        self.calls: dict[str, CallRow] = {}
        self.outputs: dict[str, _Output] = {}
        self.last_ts = 0.0
        self.model = ""
        self.hooks = hook_join.Hooks()

    def mark(self, found: marks.Found, ts: float, prompt: int) -> MarkRow:
        """Turn a found mark into a row; carry it if it sits in context."""
        row = MarkRow(
            Where(prompt, ts, self.model),
            found.kind,
            found.name,
            detail=found.detail,
            count=found.count,
            tokens=found.tokens,
            extra=found.extra,
            duration_ms=found.duration_ms,
        )
        self.rows.marks.append(row)
        if row.tokens and found.kind not in marks.NOT_IN_CONTEXT:
            self.tracker.result(row.cost, row.tokens)
        self.hooks.track(row, found)
        return row

    def record(self, rec: dict[str, Any], ts: float, prompt: int) -> None:
        """Account one record (after the walker opened any new prompt)."""
        kind = rec.get("type")
        if kind == "assistant":
            self.assistant(rec, ts, prompt)
        elif kind == "user" and blocks.prompt_text(rec) is not None:
            self.hooks.prompt_opened()
        self.last_ts = ts
        for found in marks.of_record(rec):
            self.mark(found, ts, prompt)

    def assistant(self, rec: dict[str, Any], ts: float, prompt: int) -> None:
        """Error placeholders become marks; real messages add visible output."""
        message = _message(rec)
        if rec.get("isApiErrorMessage"):
            text = blocks.text_of(message.get("content"))
            detail = str(rec.get("apiError") or text)[: classify.TARGET_CHARS]
            name = str(rec.get("error") or "unknown")
            self.mark(marks.Found("api_error", name, detail=detail), ts, prompt)
            return
        mid = str(message.get("id") or "")
        if mid not in self.outputs:
            self.outputs[mid] = _Output(max(0.0, ts - (self.last_ts or ts)))
        for block in parse.content_blocks(rec):
            self.outputs[mid].add(block)

    def use(
        self, rec: dict[str, Any], block: dict[str, Any], ts: float, prompt: int
    ) -> None:
        """Open a call row for a ``tool_use`` block."""
        message = _message(rec)
        raw = block.get("input")
        tool_input: dict[str, object] = raw if isinstance(raw, dict) else {}
        name = str(block.get("name") or "unknown")
        row = CallRow(
            Where(prompt, ts, str(message.get("model") or self.model)),
            name=name,
            family=classify.family(name, tool_input),
            target=classify.target(name, tool_input),
            sig=classify.signature(name, tool_input),
            message_id=str(message.get("id") or ""),
        )
        self.calls[str(block.get("id") or "")] = row
        self.rows.calls.append(row)

    def result(self, block: dict[str, Any], ts: float) -> None:
        """Close the call a ``tool_result`` answers."""
        row = self.calls.pop(str(block.get("tool_use_id") or ""), None)
        if row is None:
            return
        content = block.get("content")
        images, text = marks.split_images(content)
        row.end_ts = ts
        row.images = images
        row.result_tokens = images * parse.IMAGE_TOKENS + len(text) // CHARS
        if block.get("is_error"):
            row.error_kind = classify.error_kind(blocks.text_of(content))
        self.tracker.result(row.cost, row.result_tokens)

    def turn(self, turn: Turn, cost: float, prompt: int) -> None:
        """Note a priced API call."""
        usage = turn.usage
        self.model = turn.model
        self.tracker.turn(turn.model, turn.context, write_multiplier(usage))
        self.hooks.turn(cost, turn.timestamp)
        output = self.outputs.pop(turn.message_id, None) or _Output(0.0)
        text, tool, think = output.split(usage.get("output_tokens", 0))
        one_hour = usage.get(records.CACHE_1H, 0)
        self.rows.turns.append(
            TurnDetail(
                Where(prompt, turn.timestamp, turn.model),
                latency_s=output.latency,
                cw_1h=one_hour,
                cw_5m=usage.get("cache_creation_input_tokens", 0) - one_hour,
                out_text=text,
                out_tool=tool,
                out_think=think,
                tool_calls=turn.tool_calls,
            )
        )

    def finish(self, book: PriceBook) -> DetailRows:
        """Settle costs, fill batch sizes and models, merge repeated marks."""
        self.tracker.settle(book)
        per_message: dict[str, int] = {}
        for call in self.rows.calls:
            per_message[call.message_id] = per_message.get(call.message_id, 0) + 1
        for call in self.rows.calls:
            call.batch = per_message[call.message_id]
        first_model = self.rows.turns[0].where.model if self.rows.turns else ""
        self.hooks.resolve()
        self.rows.marks = hook_join.merge(self.rows.marks, first_model)
        return self.rows
