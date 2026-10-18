"""Derive per-session, per-prompt and per-subagent summaries from raw rows.

Run for every main session touched by an ingest pass. A subagent file may be
ingested in a different pass than its parent, so everything here is computed
from the store, never from the in-memory walk.

Linking a subagent to the prompt that spawned it: the ``toolUseId`` in its
``.meta.json`` (or the ``agentId`` the ``Agent`` result reported) names an
``Agent`` call; that call's prompt is the answer. A depth-2 agent's call sits
in its parent agent's file, so the chain is followed upward. An agent with no
resolvable spawn -- one that outlived ``/clear`` -- stays ``prompt_idx NULL``
("unattributed") rather than being dropped, so session cost always reconciles.
"""

from __future__ import annotations

from collections import defaultdict
import json
from typing import TYPE_CHECKING, Any

from python_pkg.token_dashboard import active

if TYPE_CHECKING:
    import sqlite3

_MAX_DEPTH = 8


def _rows(conn: sqlite3.Connection, sql: str, *args: object) -> list[Any]:
    """Run a query and return all rows."""
    return conn.execute(sql, args).fetchall()


class _Session:
    """Everything stored for one main session and its subagents."""

    def __init__(self, conn: sqlite3.Connection, main: str) -> None:
        self.main = main
        self.sessions = {
            r[0]: r
            for r in _rows(
                conn,
                "SELECT key, cwd, agent_type, description, spawn_tool_use_id,"
                " agent_model, first_ts, last_ts, final_tag"
                " FROM sessions WHERE main_key = ?",
                main,
            )
        }
        self.turns = _rows(
            conn,
            "SELECT key, prompt_idx, usd, model FROM turns WHERE main_key = ?",
            main,
        )
        keys = json.dumps(list(self.sessions))
        self.calls = _rows(
            conn,
            "SELECT key, tool_use_id, agent_id, prompt_idx, description,"
            " subagent_type FROM agent_calls WHERE key IN"
            " (SELECT value FROM json_each(?))",
            keys,
        )
        self.spans_by_key: dict[str, list[active.Span]] = defaultdict(list)
        for key, start, end in _rows(
            conn,
            "SELECT key, start, end FROM activity WHERE key IN"
            " (SELECT value FROM json_each(?))",
            keys,
        ):
            self.spans_by_key[key].append((start, end))
        self.spans = [s for spans in self.spans_by_key.values() for s in spans]
        self.prompts = _rows(
            conn,
            "SELECT idx, ts, text FROM prompts WHERE key = ? ORDER BY idx",
            main,
        )
        self.usd: dict[str, float] = defaultdict(float)
        self.ncalls: dict[str, int] = defaultdict(int)
        self.models: dict[str, dict[str, float]] = defaultdict(
            lambda: defaultdict(float)
        )
        for key, _, usd, model in self.turns:
            self.usd[key] += usd
            self.ncalls[key] += 1
            self.models[key][model] += usd

    def spawn(self, sub: str) -> tuple[Any, ...] | None:
        """The ``Agent`` call that spawned ``sub``, if any is stored."""
        tool_use_id = self.sessions[sub][4]
        agent_id = sub.rsplit("/agent-", 1)[-1]
        for call in self.calls:
            if (tool_use_id and call[1] == tool_use_id) or call[2] == agent_id:
                return tuple(call)
        return None

    def resolve(self, sub: str) -> tuple[int | None, int, tuple[Any, ...] | None]:
        """``(prompt_idx, depth, spawning call)`` for a subagent."""
        first = self.spawn(sub)
        call, depth = first, 1
        while call is not None and call[0] != self.main and depth < _MAX_DEPTH:
            call = self.spawn(call[0]) if call[0] in self.sessions else None
            depth += 1
        return (call[3] if call is not None else None), depth, first


def _sub_rows(state: _Session) -> list[tuple[Any, ...]]:
    """One ``subagent_link`` row per subagent of the session."""
    out = []
    for key, row in state.sessions.items():
        if key == state.main:
            continue
        prompt_idx, depth, call = state.resolve(key)
        models = state.models.get(key) or {}
        model = max(models, key=models.__getitem__) if models else row[5]
        spans = state.spans_by_key.get(key, [])
        out.append(
            (
                key,
                state.main,
                prompt_idx,
                depth,
                row[3] or (call[4] if call else "") or key,
                row[2] or (call[5] if call else "") or "unknown",
                model,
                state.usd.get(key, 0.0),
                state.ncalls.get(key, 0),
                row[6],
                row[7],
                row[7] - row[6],
                active.measure(spans),
            )
        )
    return out


def refresh(conn: sqlite3.Connection, main: str) -> None:
    """Rebuild every summary row for one main session."""
    state = _Session(conn, main)
    conn.execute("DELETE FROM subagent_link WHERE main_key = ?", (main,))
    conn.execute("DELETE FROM prompt_summary WHERE key = ?", (main,))
    conn.execute("DELETE FROM session_summary WHERE key = ?", (main,))
    if not state.sessions:
        return
    subs = _sub_rows(state)
    conn.executemany(
        "INSERT INTO subagent_link VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", subs
    )
    first = min((r[6] for r in state.sessions.values() if r[6]), default=0.0)
    last = max(r[7] for r in state.sessions.values())
    _prompt_rows(conn, state, subs, last)
    own = state.sessions.get(main)
    usd_main = state.usd.get(main, 0.0)
    usd_sub = sum(r[7] for r in subs)
    merged: dict[str, float] = defaultdict(float)
    for models in state.models.values():
        for model, usd in models.items():
            merged[model] += usd
    conn.execute(
        "INSERT INTO session_summary VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            main,
            own[1] if own else next(iter(state.sessions.values()))[1],
            state.prompts[0][2] if state.prompts else (subs[0][4] if subs else ""),
            first,
            last,
            last - first,
            active.measure(state.spans),
            usd_main + usd_sub,
            usd_main,
            usd_sub,
            sum(state.ncalls.values()),
            len(state.prompts),
            len(subs),
            json.dumps(dict(merged)),
            own[8] if own else None,
        ),
    )


def _prompt_rows(
    conn: sqlite3.Connection,
    state: _Session,
    subs: list[tuple[Any, ...]],
    last: float,
) -> None:
    """One ``prompt_summary`` row per prompt, plus one for pre-prompt turns."""
    own: dict[int, float] = defaultdict(float)
    calls: dict[int, int] = defaultdict(int)
    for key, idx, usd, _ in state.turns:
        if key == state.main:
            own[idx] += usd
            calls[idx] += 1
    sub_usd: dict[int, float] = defaultdict(float)
    for row in subs:
        if row[2] is not None:
            sub_usd[row[2]] += row[7]
    prompts = list(state.prompts)
    if own.get(-1) or sub_usd.get(-1):
        start = min((s for s, _ in state.spans), default=0.0)
        prompts.insert(0, (-1, start, "(before the first prompt)"))
    bounds = [ts for _, ts, _ in prompts[1:]] + ([last + 1] if prompts else [])
    conn.executemany(
        "INSERT INTO prompt_summary VALUES (?,?,?,?,?,?,?,?,?)",
        [
            (
                state.main,
                idx,
                ts,
                text,
                own.get(idx, 0.0),
                sub_usd.get(idx, 0.0),
                active.measure(state.spans, ts, end),
                min(end, last) - ts,
                calls.get(idx, 0),
            )
            for (idx, ts, text), end in zip(prompts, bounds, strict=True)
        ],
    )
