"""Three 0-token efficiency trends, weekly.

1. **USD per DONE session** -- all spend of status-tagged sessions in a week
   divided by how many of them ended on ``DONE:``. Failed and parked sessions
   count against the done ones, which is the point. Sessions with no tag at all
   (before the convention) are counted but kept out of the ratio.
2. **USD per surviving commit** -- the week's total spend divided by commits
   made that week that survived :mod:`survival`'s 14-day rule.
3. **USD per estimated size unit** -- spend of sessions the task-size estimator
   sized, divided by the sum of its ``est_calls`` for them.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
from typing import TYPE_CHECKING, Any

from python_pkg.token_dashboard import survival

if TYPE_CHECKING:
    from collections.abc import Iterable
    import sqlite3

Week = dict[str, Any]


@dataclass(frozen=True)
class SessionCost:
    """What one main session cost and how it ended."""

    key: str
    first_ts: float
    usd: float
    tag: str | None


def week_of(stamp: float) -> str:
    """Monday (local time) of the week containing ``stamp``."""
    day = datetime.fromtimestamp(stamp).astimezone().date()
    return (day - timedelta(days=day.weekday())).isoformat()


def _ratio(part: float, whole: float) -> float | None:
    """``part / whole``, ``None`` when ``whole`` is zero."""
    return part / whole if whole else None


def done_weekly(rows: Iterable[SessionCost]) -> list[Week]:
    """USD per DONE session and the DONE share, per week."""
    weeks: dict[str, Week] = defaultdict(
        lambda: {"done": 0, "other": 0, "untagged": 0, "usd_tagged": 0.0}
    )
    for row in rows:
        week = weeks[week_of(row.first_ts)]
        if row.tag is None:
            week["untagged"] += 1
            continue
        week["usd_tagged"] += row.usd
        week["done" if row.tag == "DONE" else "other"] += 1
    out = []
    for name in sorted(weeks):
        week = weeks[name]
        tagged = week["done"] + week["other"]
        week |= {
            "week": name,
            "usd_per_done": _ratio(week["usd_tagged"], week["done"]),
            "done_share": _ratio(week["done"], tagged),
        }
        out.append(week)
    return out


def commits_weekly(
    verdicts: Iterable[tuple[float, str]], week_usd: dict[str, float]
) -> list[Week]:
    """USD per surviving commit, with lost / pending / unknown counts."""
    weeks: dict[str, Week] = defaultdict(
        lambda: {"survived": 0, "lost": 0, "pending": 0, "unknown": 0}
    )
    for stamp, verdict in verdicts:
        week = weeks[week_of(stamp)]
        if verdict == "survived":
            week["survived"] += 1
        elif verdict in survival.FINAL:
            week["lost"] += 1
        elif verdict == "pending":
            week["pending"] += 1
        else:
            week["unknown"] += 1
    out = []
    for name in sorted(weeks):
        usd = week_usd.get(name, 0.0)
        week = weeks[name]
        week |= {
            "week": name,
            "usd": usd,
            "usd_per_survivor": _ratio(usd, week["survived"]),
        }
        out.append(week)
    return out


def estimate_weekly(rows: Iterable[SessionCost], est: dict[str, int]) -> list[Week]:
    """USD per estimated call, over sessions the estimator sized."""
    weeks: dict[str, Week] = defaultdict(lambda: {"usd": 0.0, "est_calls": 0, "n": 0})
    for row in rows:
        if row.key not in est:
            continue
        week = weeks[week_of(row.first_ts)]
        week["usd"] += row.usd
        week["est_calls"] += est[row.key]
        week["n"] += 1
    return [
        weeks[name]
        | {
            "week": name,
            "usd_per_unit": _ratio(weeks[name]["usd"], weeks[name]["est_calls"]),
        }
        for name in sorted(weeks)
    ]


def rebuild(conn: sqlite3.Connection, now: float) -> None:
    """Recompute the three weekly series into ``meta['efficiency']``."""
    rows = [
        SessionCost(key, first, usd, tag)
        for key, first, usd, tag in conn.execute(
            "SELECT key, first_ts, usd, final_tag FROM session_summary"
        )
    ]
    week_usd: dict[str, float] = defaultdict(float)
    for row in rows:
        week_usd[week_of(row.first_ts)] += row.usd
    judged = conn.execute(
        "SELECT c.ts, v.verdict FROM session_commits c"
        " LEFT JOIN commit_verdicts v ON v.sha = c.sha"
    ).fetchall()
    verdicts = [
        (ts, verdict or ("pending" if now - ts < survival.WINDOW_S else "unchecked"))
        for ts, verdict in judged
    ]
    est = dict(conn.execute("SELECT session_id, est_calls FROM estimates"))
    payload = {
        "done": done_weekly(rows),
        "commits": commits_weekly(verdicts, week_usd),
        "estimate": estimate_weekly(rows, est),
    }
    conn.execute(
        "INSERT OR REPLACE INTO meta VALUES ('efficiency', ?)", (json.dumps(payload),)
    )
