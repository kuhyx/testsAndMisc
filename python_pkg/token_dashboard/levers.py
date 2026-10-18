"""Every lever ever applied, proposed or passed over, with its outcome.

Sources, newest form first:

* ``history/*.json`` ``levers`` -- structured candidates (snapshots from
  2026-10-18 on; see ``token_audit.review``).
* Markdown "Candidate levers" tables -- for older snapshots. WEEKLY.md is
  overwritten every run, so older tables survive only in transcript tool
  results; :mod:`walk` keeps those as ``lever_tables`` rows.
* ``ledger.jsonl`` -- applied levers, scored by ``token_audit.history.score``.
* ``prune/<date>/PROPOSAL.md`` -- weekly standing-prefix prune proposals.

Status of a candidate: ``applied`` if a ledger line on the same metric is dated
on or after the snapshot, ``not applied`` if a newer snapshot came and went
without one, else ``proposed``. Titles never match ledger text, so the join is
on the metric key.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

from python_pkg.token_audit import history
from python_pkg.token_audit.recommend import TITLE_METRIC

if TYPE_CHECKING:
    from pathlib import Path

Row = dict[str, Any]
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_COLUMNS = 5


def parse_candidates(markdown: str) -> list[Row]:
    """Rows of a ``| category | lever | evidence | est $/day | action |`` table."""
    rows = []
    for line in markdown.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != _COLUMNS or cells[0] in {"category", ""}:
            continue
        if set(cells[0]) <= {"-"}:
            continue
        est = cells[3].lstrip("$").replace(",", "")
        rows.append(
            {
                "category": cells[0],
                "title": cells[1],
                "evidence": cells[2],
                "est_usd_per_day": float(est)
                if est.replace(".", "").isdigit()
                else None,
                "action": cells[4],
                "metric": TITLE_METRIC.get(cells[1], ""),
            }
        )
    return rows


def ledger_date(entry: Row) -> str | None:
    """A ledger line's date, else one named in its text (prune lines)."""
    if isinstance(entry.get("date"), str):
        return str(entry["date"])
    found = DATE.search(str(entry.get("lever", "")))
    return found.group(0) if found else None


def _snapshots(report: Path) -> list[tuple[str, Row]]:
    """``(date, snapshot)`` oldest first."""
    out = []
    for path in sorted((report / "history").glob("*.json")):
        try:
            snap = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            continue
        if isinstance(snap, dict):
            out.append((path.stem[:10], snap))
    return out


def _applied(report: Path, latest: Row) -> list[Row]:
    """Ledger lines, scored against the newest snapshot."""
    entries = history.read_ledger(report)
    rows = []
    for entry, verdict in zip(entries, history.score(entries, latest), strict=True):
        rows.append(
            {
                "source": "ledger",
                "date": ledger_date(entry),
                "lever": verdict.lever,
                "metric": verdict.metric,
                "baseline": verdict.baseline,
                "predicted": verdict.predicted,
                "actual": verdict.actual,
                "lower_is_better": int(bool(entry.get("lower_is_better", True))),
                "status": "applied",
                "outcome": verdict.outcome,
                "detail": f"{verdict.note}; undo: {entry.get('undo', '-')}",
            }
        )
    return rows


def _candidates(
    snaps: list[tuple[str, Row]], tables: dict[str, str], applied: list[Row]
) -> list[Row]:
    """Candidate rows per snapshot, structured first, markdown second."""
    rows = []
    for position, (day, snap) in enumerate(snaps):
        found = snap.get("levers")
        if not isinstance(found, list):
            found = parse_candidates(tables.get(day, ""))
        newer = position + 1 < len(snaps)
        for lever in found:
            metric = str(lever.get("metric") or "")
            hit = any(
                a["metric"] == metric and (a["date"] or "") >= day for a in applied
            )
            status = "applied" if hit else ("not applied" if newer else "proposed")
            rows.append(
                {
                    "source": f"snapshot {day}",
                    "date": day,
                    "lever": lever.get("title"),
                    "metric": metric,
                    "baseline": snap.get("metrics", {}).get(metric),
                    "predicted": None,
                    "actual": None,
                    "lower_is_better": 1,
                    "status": status,
                    "outcome": None,
                    "detail": f"{lever.get('evidence')} -> {lever.get('action')}"
                    f" (est ${lever.get('est_usd_per_day') or '-'}/day)",
                }
            )
    return rows


def _prunes(report: Path, applied: list[Row]) -> list[Row]:
    """One row per prune proposal."""
    paths = sorted((report / "prune").glob("*/PROPOSAL.md"))
    rows = []
    for position, path in enumerate(paths):
        day = path.parent.name
        lines = [x for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
        hit = any(f"prune {day}" in str(a["lever"]) for a in applied)
        latest = position == len(paths) - 1
        status = "applied" if hit else ("proposed" if latest else "not applied")
        rows.append(
            {
                "source": f"prune {day}",
                "date": day,
                "lever": lines[0].lstrip("# ") if lines else f"prune {day}",
                "metric": "standing_tokens_est",
                "baseline": None,
                "predicted": None,
                "actual": None,
                "lower_is_better": 1,
                "status": status,
                "outcome": None,
                "detail": lines[1] if len(lines) > 1 else "",
            }
        )
    return rows


def build(report: Path, tables: dict[str, str]) -> list[Row]:
    """Every lever row, applied ones first."""
    snaps = _snapshots(report)
    latest = snaps[-1][1] if snaps else {}
    applied = _applied(report, latest)
    return applied + _candidates(snaps, tables, applied) + _prunes(report, applied)
