"""Join hook context to the run that produced it; price forced retries; merge.

``hook_additional_context`` names no command, so it is matched to a
``hook_success`` run of the same tool-use id and hook name whose stdout
contains the context text. A ``hook_blocking_error`` costs the calls it
forces: a Stop bounce every call until the next prompt, any other block the
one call that reacts to it.
"""

from __future__ import annotations

from dataclasses import replace
import json
from typing import TYPE_CHECKING

from python_pkg.token_dashboard.marks import SNIPPET

if TYPE_CHECKING:
    from python_pkg.token_dashboard.detail_rows import MarkRow
    from python_pkg.token_dashboard.marks import Found

_STOPS = frozenset({"Stop", "SubagentStop"})


class Hooks:
    """Pending joins and open retry windows for one file."""

    def __init__(self) -> None:
        """Nothing seen yet."""
        self.runs: dict[tuple[str, str], list[tuple[str, str]]] = {}
        self.pending: list[tuple[MarkRow, tuple[str, str], str]] = []
        self.until_prompt: list[MarkRow] = []
        self.next_turn: list[MarkRow] = []

    def track(self, row: MarkRow, found: Found) -> None:
        """Remember what later records or turns need to complete ``row``."""
        if found.kind == "hook_run":
            self.runs.setdefault(found.key, []).append((row.detail, found.text))
        elif found.kind == "hook_context":
            self.pending.append((row, found.key, found.text))
        elif found.kind == "hook_block":
            stop = row.name in _STOPS
            (self.until_prompt if stop else self.next_turn).append(row)

    def prompt_opened(self) -> None:
        """A new prompt ends every Stop-bounce retry."""
        self.until_prompt.clear()

    def turn(self, cost: float, ts: float) -> None:
        """Charge an API call made after a block to that block's retry.

        Turns are released one message late, so a turn released after the
        block record may still predate it: the timestamp decides.
        """
        for row in [*self.until_prompt, *self.next_turn]:
            if ts > row.where.ts:
                row.retry_usd += cost
        self.next_turn = [row for row in self.next_turn if ts <= row.where.ts]

    def resolve(self) -> None:
        """Name the script behind each injected hook context."""
        for row, key, text in self.pending:
            snippet = text[:SNIPPET]
            escaped = json.dumps(snippet)[1:-1]
            for detail, stdout in self.runs.get(key, []):
                if snippet and (snippet in stdout or escaped in stdout):
                    row.detail = detail
                    break


def merge(rows: list[MarkRow], first_model: str) -> list[MarkRow]:
    """Sum marks sharing prompt, kind, name, detail and model; oldest first."""
    merged: dict[tuple[int, str, str, str, str], MarkRow] = {}
    for row in rows:
        row.where = replace(row.where, model=row.where.model or first_model)
        where = row.where
        key = (where.prompt_idx, row.kind, row.name, row.detail, where.model)
        held = merged.get(key)
        if held is None:
            merged[key] = row
            continue
        held.where = replace(held.where, ts=min(held.where.ts, where.ts))
        held.count += row.count
        held.tokens += row.tokens
        held.extra += row.extra
        held.duration_ms += row.duration_ms
        held.retry_usd += row.retry_usd
        held.cost.create_usd += row.cost.create_usd
        held.cost.carry_usd += row.cost.carry_usd
        held.cost.carry_calls += row.cost.carry_calls
    return sorted(merged.values(), key=lambda r: r.where.ts)
