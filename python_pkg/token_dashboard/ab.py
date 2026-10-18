"""A/B test of judgment subagents: Sonnet arm vs Opus arm, 0 tokens.

Assignments come from ``~/.claude/logs/agent-ab.jsonl`` (one line per
dispatched review/debug/design/plan agent: ``tool_use_id``, ``arm``, ...).
Each is joined on ``tool_use_id`` to the ``Agent`` call the ingester stored,
and judged on outcomes visible in the transcript after the agent returned:

* **redo** -- the parent dispatched another Agent in the same session whose
  description shares >= :data:`REDO_JACCARD` of its word set;
* **follow-up** -- the parent sent that agent a ``SendMessage``;
* **error** -- the call errored or the agent was aborted;
* **correction** (noisy) -- the next user prompt opens with a correction
  phrase (:data:`CORRECTION`);
* the parent session's end tag.

Rates get 95% Wilson intervals and per-arm differences Newcombe's hybrid
interval. The banner turns RED only when, with >= :data:`MIN_N` per arm, the
Sonnet arm's redo or correction rate is higher and the two Wilson intervals do
not overlap.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
import re
from typing import TYPE_CHECKING, Any

from python_pkg.token_dashboard import ab_rows

if TYPE_CHECKING:
    import sqlite3

LOG = Path.home() / ".claude" / "logs" / "agent-ab.jsonl"
Z = 1.96
MIN_N = 20
REDO_JACCARD = 0.6
ERRORS = frozenset({"error", "aborted", "killed", "failed", "cancelled"})
CORRECTION = re.compile(
    r"^\W*no\b|\bwrong\b|\bthat'?s not\b|\bthat is not\b|\bincorrect\b"
    r"|\brevert\b|\byou missed\b",
    re.IGNORECASE,
)
WORD = re.compile(r"[a-z0-9]+")
RATES = ("redo", "followup", "error", "correction")


def wilson(k: int, n: int, z: float = Z) -> tuple[float, float]:
    """95% Wilson score interval for ``k`` successes in ``n`` trials."""
    if n == 0:
        return 0.0, 1.0
    p = k / n
    centre = p + z * z / (2 * n)
    spread = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    denom = 1 + z * z / n
    return max(0.0, (centre - spread) / denom), min(1.0, (centre + spread) / denom)


def diff_ci(k1: int, n1: int, k2: int, n2: int) -> tuple[float, float, float]:
    """``p1 - p2`` with Newcombe's hybrid-score 95% interval."""
    p1, p2 = (k1 / n1 if n1 else 0.0), (k2 / n2 if n2 else 0.0)
    l1, u1 = wilson(k1, n1)
    l2, u2 = wilson(k2, n2)
    diff = p1 - p2
    low = diff - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2)
    high = diff + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)
    return diff, low, high


def jaccard(a: str, b: str) -> float:
    """Word-set Jaccard similarity of two descriptions."""
    left, right = set(WORD.findall(a.lower())), set(WORD.findall(b.lower()))
    union = left | right
    return len(left & right) / len(union) if union else 0.0


def is_correction(text: str) -> bool:
    """Whether a user prompt reads as correcting the previous answer."""
    return CORRECTION.search(text) is not None


@dataclass(frozen=True)
class ArmCounts:
    """What the banner needs from one arm."""

    n: int
    redo: int
    correction: int


def banner(sonnet: ArmCounts, opus: ArmCounts) -> dict[str, str]:
    """RED / GREEN / GREY verdict for the top of every /tokens view."""
    n = min(sonnet.n, opus.n)
    if n < MIN_N:
        return {"level": "grey", "text": f"A/B judgment agents: collecting (n={n})"}
    for name in ("redo", "correction"):
        ks, ko = getattr(sonnet, name), getattr(opus, name)
        low_s, _ = wilson(ks, sonnet.n)
        _, high_o = wilson(ko, opus.n)
        if ks / sonnet.n > ko / opus.n and low_s > high_o:
            return {
                "level": "red",
                "text": f"QUALITY DROP: Sonnet {name} rate {ks}/{sonnet.n} vs Opus "
                f"{ko}/{opus.n} (95% CIs do not overlap)",
            }
    return {
        "level": "green",
        "text": f"A/B judgment agents: no detectable drop (n={n})",
    }


def _assignments(log: Path) -> list[dict[str, Any]]:
    """Well-formed assignment lines."""
    if not log.is_file():
        return []
    rows = []
    for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict) and row.get("tool_use_id") and row.get("arm"):
            rows.append(row)
    return rows


def _outcome(conn: sqlite3.Connection, tool_use_id: str) -> dict[str, Any] | None:
    """The joined call: cost, duration and the four flags, or ``None``."""
    call = conn.execute(
        "SELECT key, agent_id, ts, description, result_ts, status FROM agent_calls"
        " WHERE tool_use_id = ?",
        (tool_use_id,),
    ).fetchone()
    if call is None:
        return None
    key, agent_id, ts, desc, result_ts, status = call
    main = key.split("/", 1)[0]
    sub = conn.execute(
        "SELECT usd, wall_s, last_ts FROM subagent_link WHERE sub_key = ?",
        (f"{main}/agent-{agent_id}",),
    ).fetchone() or (0.0, (result_ts or ts) - ts, result_ts or ts)
    returned = max(result_ts or ts, sub[2] or 0)
    later = conn.execute(
        "SELECT description FROM agent_calls WHERE key = ? AND ts > ?",
        (key, returned),
    ).fetchall()
    followup = conn.execute(
        "SELECT COUNT(*) FROM sent_messages WHERE key = ? AND to_agent = ? AND ts > ?",
        (key, agent_id, returned),
    ).fetchone()[0]
    nxt = conn.execute(
        "SELECT text FROM prompts WHERE key = ? AND ts > ? ORDER BY ts LIMIT 1",
        (main, returned),
    ).fetchone()
    tag = conn.execute(
        "SELECT final_tag FROM session_summary WHERE key = ?", (main,)
    ).fetchone()
    return {
        "key": key,
        "ts": ts,
        "usd": sub[0] or 0.0,
        "duration_s": sub[1] or 0.0,
        "redo": any(jaccard(desc, d) >= REDO_JACCARD for (d,) in later),
        "followup": followup > 0,
        "error": (status or "").lower() in ERRORS,
        "correction": nxt is not None and is_correction(nxt[0]),
        "tag": (tag[0] if tag else None) or "untagged",
    }


def _mean_ci(values: list[float]) -> dict[str, float]:
    """Mean with a normal-approximation 95% interval."""
    n = len(values)
    if n == 0:
        return {"mean": 0.0, "low": 0.0, "high": 0.0}
    mean = sum(values) / n
    var = sum((v - mean) ** 2 for v in values) / (n - 1) if n > 1 else 0.0
    half = Z * math.sqrt(var / n)
    return {"mean": mean, "low": mean - half, "high": mean + half}


def _arm(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Per-arm summary."""
    n = len(rows)
    out: dict[str, Any] = {"n": n}
    for name in RATES:
        k = sum(1 for r in rows if r[name])
        low, high = wilson(k, n)
        out[name] = {"k": k, "rate": k / n if n else None, "low": low, "high": high}
    out["usd"] = _mean_ci([r["usd"] for r in rows])
    out["duration_s"] = _mean_ci([r["duration_s"] for r in rows])
    tags: dict[str, int] = {}
    for r in rows:
        tags[r["tag"]] = tags.get(r["tag"], 0) + 1
    out["tags"] = tags
    return out


def rebuild(conn: sqlite3.Connection, log: Path | None = None) -> dict[str, Any]:
    """Join every assignment, summarise both arms, store in ``meta['ab']``."""
    joined: dict[str, list[dict[str, Any]]] = {"sonnet": [], "opus": []}
    kept: list[tuple[str, str, dict[str, Any]]] = []
    unjoined = 0
    for row in _assignments(log or LOG):
        found = _outcome(conn, str(row["tool_use_id"]))
        if found is None or row["arm"] not in joined:
            unjoined += 1
            continue
        joined[row["arm"]].append(found)
        kept.append((row["arm"], str(row["tool_use_id"]), found))
    ab_rows.store(conn, kept)
    arms = {name: _arm(rows) for name, rows in joined.items()}
    diffs = {
        name: dict(
            zip(
                ("diff", "low", "high"),
                diff_ci(
                    arms["sonnet"][name]["k"],
                    arms["sonnet"]["n"],
                    arms["opus"][name]["k"],
                    arms["opus"]["n"],
                ),
                strict=True,
            )
        )
        for name in RATES
    }
    counts = {
        name: ArmCounts(
            arms[name]["n"], arms[name]["redo"]["k"], arms[name]["correction"]["k"]
        )
        for name in joined
    }
    payload = {
        "arms": arms,
        "diffs": diffs,
        "unjoined": unjoined,
        "banner": banner(counts["sonnet"], counts["opus"]),
    }
    conn.execute("INSERT OR REPLACE INTO meta VALUES ('ab', ?)", (json.dumps(payload),))
    return payload
