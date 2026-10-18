"""Walk one transcript file into the rows the store keeps for it.

Reuses token_audit's record primitives -- line loading, usage extraction,
per-API-message dedup (:class:`TurnMerger`) and list-price pricing -- rather
than :func:`parse.iter_events`, because the dashboard also needs what that
stream drops: every record's timestamp (active time), prompt boundaries, the
``Agent`` calls that spawned subagents, and commit hashes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from python_pkg.token_audit import discover, parse, pricing, records, turns
from python_pkg.token_dashboard import active, blocks, carry, detail
from python_pkg.token_dashboard.blocks import PROMPT_CHARS
from python_pkg.token_dashboard.rows import (
    AgentCall,
    Commit,
    FileFacts,
    PromptRow,
    ToolRow,
    TurnRow,
)

if TYPE_CHECKING:
    from pathlib import Path

    from python_pkg.token_audit.model import Turn

__all__ = ["NO_TOOL", "PROMPT_CHARS", "FileFacts", "walk_file"]

NO_TOOL = "(no tool)"
AGENT_TOOLS = frozenset({"Agent", "Task"})
_BOOK = pricing.load()


class _Walker:
    """Single pass over a file's records, holding the cross-record state."""

    def __init__(self, facts: FileFacts) -> None:
        self.facts = facts
        self.prompt = -1
        self.ts = 0.0
        self.stamps: list[float] = []
        self.pending: dict[str, dict[str, Any]] = {}
        self.names: dict[str, list[str]] = {}
        self.use_ts: dict[str, float] = {}
        self.tools: dict[tuple[int, str], ToolRow] = {}
        self.carry = carry.Tracker()
        self.detail = detail.Detail()
        self.merger = records.TurnMerger()
        self.last_text = ""

    def tool(self, name: str) -> ToolRow:
        """The accumulator for ``name`` in the current prompt."""
        return self.tools.setdefault((self.prompt, name), ToolRow(self.prompt, name))

    def release(self, turn: Turn | None) -> None:
        """Price a completed API call and split it across its tools."""
        if turn is None:
            return
        cost = pricing.usd(turn, _BOOK)
        usage = turn.usage
        self.facts.rows.turns.append(
            TurnRow(
                turn.timestamp or self.ts,
                turn.model,
                cost,
                turn.context,
                self.prompt,
                usage,
            )
        )
        self.carry.turn(turn.model, turn.context)
        self.detail.turn(turn, cost, self.prompt)
        names = self.names.pop(turn.message_id, []) or [NO_TOOL]
        for name in names:
            self.tool(name).usd += cost / len(names)

    def record(self, rec: dict[str, Any]) -> None:
        """Account one record."""
        stamp = records.timestamp(rec)
        if stamp is not None:
            self.ts = stamp
            self.stamps.append(stamp)
        if self.facts.cwd is None and isinstance(rec.get("cwd"), str):
            self.facts.cwd = rec["cwd"]
        if rec.get("type") == "user":
            self.release(self.merger.flush())
            self.user(rec)
        self.detail.record(rec, self.ts, self.prompt)
        for block in parse.content_blocks(rec):
            self.block(rec, block)
        found = turns.usage_of(rec)
        if found is not None:
            self.release(self.merger.push(turns.build_turn(rec, *found)))

    def user(self, rec: dict[str, Any]) -> None:
        """Open a new prompt when this user record is one."""
        text = blocks.prompt_text(rec)
        if text is None or self.facts.parent_session is not None:
            return
        self.prompt += 1
        prompt_id = rec.get("promptId")
        self.facts.rows.prompts.append(
            PromptRow(self.prompt, self.ts, str(prompt_id or ""), text)
        )

    def block(self, rec: dict[str, Any], block: dict[str, Any]) -> None:
        """Remember tool calls, pair results, keep the last reply text."""
        kind = block.get("type")
        if kind == "tool_use":
            self.tool_use(rec, block)
        elif kind == "tool_result":
            self.tool_result(rec, block)
        elif kind == "text" and rec.get("type") == "assistant":
            self.last_text = str(block.get("text") or "")

    def tool_use(self, rec: dict[str, Any], block: dict[str, Any]) -> None:
        """Hold a call until its result arrives; note which message issued it."""
        call_id = str(block.get("id") or "")
        self.pending[call_id] = block
        self.use_ts[call_id] = self.ts
        message = rec.get("message")
        mid = message.get("id") if isinstance(message, dict) else None
        name = str(block.get("name") or "unknown")
        self.names.setdefault(str(mid or ""), []).append(name)
        self.detail.use(rec, block, self.ts, self.prompt)

    def tool_result(self, rec: dict[str, Any], block: dict[str, Any]) -> None:
        """Pair a result with its call and record what it tells us."""
        call_id = str(block.get("tool_use_id") or "")
        use = self.pending.get(call_id)
        paired = parse.pair_result(block, self.pending)
        if use is None or paired is None:
            return
        self.detail.result(block, self.ts)
        row = self.tool(paired.name)
        row.calls += 1
        row.result_tokens += paired.result_tokens
        self.carry.result(row, paired.result_tokens)
        text = blocks.text_of(block.get("content"))
        raw_input = use.get("input")
        tool_input: dict[str, Any] = raw_input if isinstance(raw_input, dict) else {}
        if paired.name in AGENT_TOOLS:
            failed = bool(block.get("is_error"))
            self.agent_call(rec, call_id, tool_input, failed=failed)
        elif paired.name == "SendMessage":
            self.facts.rows.messages.append((self.ts, str(tool_input.get("to") or "")))
        if paired.commit:
            # Every commit command is kept, hash or not: most run through
            # finish_auto.sh with a tailed or backgrounded output, so the hash
            # is usually found later by :mod:`commits` from git log instead.
            hint = blocks.repo_hint(str(tool_input.get("command")), self.facts.cwd)
            started = self.use_ts.pop(call_id, self.ts)
            self.facts.rows.commits += [
                Commit(self.prompt, started, self.ts, sha, hint)
                for sha in blocks.commit_shas(text) or [""]
            ]
        table = blocks.lever_table(text)
        if table is not None:
            self.facts.rows.lever_tables.append((self.ts, table))

    def agent_call(
        self,
        rec: dict[str, Any],
        call_id: str,
        tool_input: dict[str, Any],
        *,
        failed: bool,
    ) -> None:
        """Record a subagent spawn with the ``agentId`` its result names."""
        result = rec.get("toolUseResult")
        result = result if isinstance(result, dict) else {}
        agent_id = result.get("agentId")
        status = "error" if failed else str(result.get("status") or "")
        self.facts.rows.agent_calls.append(
            AgentCall(
                tool_use_id=call_id,
                agent_id=str(agent_id or ""),
                prompt_idx=self.prompt,
                ts=self.use_ts.get(call_id, self.ts),
                description=str(tool_input.get("description") or ""),
                subagent_type=str(tool_input.get("subagent_type") or ""),
                model=str(tool_input.get("model") or ""),
                result_ts=self.ts,
                status=status,
            )
        )

    def finish(self) -> FileFacts:
        """Flush state into the facts."""
        self.release(self.merger.flush())
        facts = self.facts
        facts.rows.tools = list(self.tools.values())
        self.carry.settle(_BOOK)
        facts.rows.detail = self.detail.finish(_BOOK)
        facts.rows.intervals = active.intervals(self.stamps)
        if self.stamps:
            facts.span = (min(self.stamps), max(self.stamps))
        facts.final_tag = blocks.final_tag(self.last_text)
        return facts


def walk_file(path: Path, root: Path) -> FileFacts:
    """Read one transcript (main or subagent) into :class:`FileFacts`."""
    del root  # keys are derived from the path's own layout
    if path.parent.name == "subagents":
        parent = path.parent.parent.name
        facts = FileFacts(
            key=f"{parent}/{path.stem}",
            session_id=parent,
            parent_session=parent,
            cwd=None,
            meta=discover.agent_meta(path),
        )
    else:
        facts = FileFacts(path.stem, path.stem, None, None, {})
    walker = _Walker(facts)
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            rec = parse.load_line(line)
            if rec is not None:
                walker.record(rec)
    return walker.finish()
