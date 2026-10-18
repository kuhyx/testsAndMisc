"""Write one file's detail rows (calls, marks, turn facts) into the store.

Every row repeats the owning file's key, main session key, subagent flag and
cwd, plus its own model, timestamp and local day, so the dashboard's shared
filter clause (date range, cwd, model, scope) applies to these tables as-is.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import sqlite3

    from python_pkg.token_dashboard.detail_rows import Cost, Where
    from python_pkg.token_dashboard.rows import FileFacts

CLEAR = (
    "DELETE FROM calls WHERE key = ?",
    "DELETE FROM marks WHERE key = ?",
    "DELETE FROM turn_detail WHERE key = ?",
)

Owner = tuple[str, str, int, str | None]


def day_of(stamp: float) -> str:
    """Local calendar day of a unix timestamp."""
    return datetime.fromtimestamp(stamp).astimezone().strftime("%Y-%m-%d")


def _where(where: Where) -> tuple[str, float, str, int]:
    """``model, ts, day, prompt_idx`` columns."""
    return (where.model, where.ts, day_of(where.ts), where.prompt_idx)


def _cost(cost: Cost) -> tuple[float, float, int]:
    """``create_usd, carry_usd, carry_calls`` columns."""
    return (cost.create_usd, cost.carry_usd, cost.carry_calls)


def write(conn: sqlite3.Connection, facts: FileFacts, owner: Owner) -> None:
    """Insert the detail rows; :func:`store.write` already cleared old ones."""
    detail = facts.rows.detail
    conn.executemany(
        "INSERT INTO calls (key, main_key, is_sub, cwd, model, ts, day,"
        " prompt_idx, end_ts, name, family, target, sig, batch, result_tokens,"
        " images, is_error, error_kind, create_usd, carry_usd, carry_calls)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            (
                *owner,
                *_where(c.where),
                c.end_ts,
                c.name,
                c.family,
                c.target,
                c.sig,
                c.batch,
                c.result_tokens,
                c.images,
                int(bool(c.error_kind)),
                c.error_kind,
                *_cost(c.cost),
            )
            for c in detail.calls
        ],
    )
    conn.executemany(
        "INSERT INTO marks (key, main_key, is_sub, cwd, model, ts, day,"
        " prompt_idx, kind, name, detail, count, tokens, extra, duration_ms,"
        " retry_usd, create_usd, carry_usd, carry_calls)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            (
                *owner,
                *_where(m.where),
                m.kind,
                m.name,
                m.detail,
                m.count,
                m.tokens,
                m.extra,
                m.duration_ms,
                m.retry_usd,
                *_cost(m.cost),
            )
            for m in detail.marks
        ],
    )
    conn.executemany(
        "INSERT INTO turn_detail (key, main_key, is_sub, cwd, model, ts, day,"
        " prompt_idx, latency_s, cw_1h, cw_5m, out_text, out_tool, out_think,"
        " tool_calls) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            (
                *owner,
                *_where(t.where),
                t.latency_s,
                t.cw_1h,
                t.cw_5m,
                t.out_text,
                t.out_tool,
                t.out_think,
                t.tool_calls,
            )
            for t in detail.turns
        ],
    )
