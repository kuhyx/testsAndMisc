"""Write one file's :class:`FileFacts` into the raw tables, replacing old rows.

The unit of change is the whole file: a changed transcript is re-walked and
its rows replaced in one transaction. Resuming from a byte offset would need
the dedup state (:class:`TurnMerger`) persisted across runs, and re-walking
even the largest transcript costs a fraction of a second.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from python_pkg.token_dashboard import detail_store
from python_pkg.token_dashboard.detail_store import day_of

if TYPE_CHECKING:
    import sqlite3

    from python_pkg.token_dashboard.walk import FileFacts

# One literal statement per raw table: no SQL is assembled from strings.
CLEAR = (
    "DELETE FROM turns WHERE key = ?",
    "DELETE FROM prompts WHERE key = ?",
    "DELETE FROM tool_use WHERE key = ?",
    "DELETE FROM agent_calls WHERE key = ?",
    "DELETE FROM activity WHERE key = ?",
    "DELETE FROM lever_tables WHERE key = ?",
    "DELETE FROM commits WHERE key = ?",
    "DELETE FROM sent_messages WHERE key = ?",
    *detail_store.CLEAR,
)


def write(
    conn: sqlite3.Connection, facts: FileFacts, path: str, stat: tuple[int, float]
) -> None:
    """Replace every row ``facts.key`` owns. Caller commits."""
    key = facts.key
    for statement in CLEAR:
        conn.execute(statement, (key,))
    main_key = facts.parent_session or key
    meta = facts.meta
    conn.execute(
        "INSERT OR REPLACE INTO sessions VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            key,
            facts.session_id,
            main_key,
            facts.cwd,
            meta.get("agentType"),
            meta.get("description"),
            meta.get("toolUseId"),
            meta.get("parentAgentId"),
            meta.get("model"),
            *facts.span,
            facts.final_tag,
        ),
    )
    is_sub = int(facts.parent_session is not None)
    conn.executemany(
        "INSERT INTO turns VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            (
                key,
                main_key,
                is_sub,
                facts.cwd,
                t.ts,
                day_of(t.ts),
                t.model,
                t.usd,
                t.context,
                t.prompt_idx,
                t.usage.get("input_tokens", 0),
                t.usage.get("cache_creation_input_tokens", 0),
                t.usage.get("cache_read_input_tokens", 0),
                t.usage.get("output_tokens", 0),
            )
            for t in facts.rows.turns
        ],
    )
    conn.executemany(
        "INSERT INTO prompts VALUES (?,?,?,?,?)",
        [(key, p.idx, p.ts, p.prompt_id, p.text) for p in facts.rows.prompts],
    )
    conn.executemany(
        "INSERT INTO tool_use VALUES (?,?,?,?,?,?,?)",
        [
            (key, t.prompt_idx, t.name, t.calls, t.result_tokens, t.usd, t.carry_usd)
            for t in facts.rows.tools
        ],
    )
    conn.executemany(
        "INSERT INTO agent_calls (key, tool_use_id, agent_id, prompt_idx, ts,"
        " description, subagent_type, model, result_ts, status)"
        " VALUES (?,?,?,?,?,?,?,?,?,?)",
        [
            (
                key,
                a.tool_use_id,
                a.agent_id,
                a.prompt_idx,
                a.ts,
                a.description,
                a.subagent_type,
                a.model,
                a.result_ts,
                a.status,
            )
            for a in facts.rows.agent_calls
        ],
    )
    conn.executemany(
        "INSERT INTO activity VALUES (?,?,?)",
        [(key, s, e) for s, e in facts.rows.intervals],
    )
    conn.executemany(
        "INSERT INTO lever_tables VALUES (?,?,?)",
        [(key, ts, md) for ts, md in facts.rows.lever_tables],
    )
    conn.executemany(
        "INSERT INTO commits (key, prompt_idx, ts, end_ts, sha, repo)"
        " VALUES (?,?,?,?,?,?)",
        [
            (key, c.prompt_idx, c.ts, c.end_ts, c.sha, c.repo)
            for c in facts.rows.commits
        ],
    )
    conn.executemany(
        "INSERT INTO sent_messages VALUES (?,?,?)",
        [(key, ts, to) for ts, to in facts.rows.messages],
    )
    detail_store.write(conn, facts, (key, main_key, is_sub, facts.cwd))
    conn.execute("INSERT OR REPLACE INTO files VALUES (?,?,?,?)", (path, key, *stat))
