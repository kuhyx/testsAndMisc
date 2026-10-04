"""Dated snapshots and the ledger of applied changes.

Until 2026-10-04 every run overwrote one ``weekly.json``, so "did last month's
change help?" had no data to answer it -- and Claude Code deletes transcripts
after ~30 days, so the raw data cannot be re-read later either. Two durable
files fix that:

* ``history/YYYY-MM-DD[-HHMM].json`` -- one snapshot per run, never rewritten.
  The newest one's window end is the next run's default start, which is how
  ``/token-optimization`` "figures out when the last analysis was".
* ``ledger.jsonl`` -- one line per applied lever: which snapshot metric it was
  meant to move, the baseline value, the predicted value, and how to undo it.
  :func:`score` turns each line into helped / no effect / regressed against the
  latest snapshot, in code, so the verdict is never an LLM's impression.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from python_pkg.token_audit.probe import PREDICTION_TOLERANCE

REPORT_DIR = Path.home() / ".claude" / "token-report"
HISTORY_NAME = "history"
LEDGER_NAME = "ledger.jsonl"
# A metric must move by more than this fraction of its baseline to count as a
# change at all; smaller moves are within week-to-week noise.
NOISE = 0.03


def _root(directory: Path | None) -> Path:
    """Resolve the report directory at call time so it can be redirected."""
    return REPORT_DIR if directory is None else directory


def save_snapshot(snap: dict[str, Any], directory: Path | None = None) -> Path:
    """Write ``snap`` under ``history/`` without ever overwriting a file."""
    folder = _root(directory) / HISTORY_NAME
    folder.mkdir(parents=True, exist_ok=True)
    now = datetime.now(tz=UTC)
    path = folder / f"{now:%Y-%m-%d}.json"
    if path.exists():
        path = folder / f"{now:%Y-%m-%d-%H%M%S}.json"
    path.write_text(json.dumps(snap, indent=2), encoding="utf-8")
    return path


def last_snapshot(directory: Path | None = None) -> dict[str, Any] | None:
    """Return the newest readable snapshot, or ``None`` if there is none."""
    folder = _root(directory) / HISTORY_NAME
    if not folder.is_dir():
        return None
    for path in sorted(folder.glob("*.json"), reverse=True):
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            continue
        if isinstance(loaded, dict):
            return loaded
    return None


def default_since(directory: Path | None = None) -> float | None:
    """The previous analysis's window end, i.e. where this one should start."""
    snap = last_snapshot(directory)
    if snap is None:
        return None
    until = snap.get("window", {}).get("until")
    return float(until) if isinstance(until, (int, float)) else None


def read_ledger(directory: Path | None = None) -> list[dict[str, Any]]:
    """Return every well-formed ledger entry, oldest first."""
    path = _root(directory) / LEDGER_NAME
    if not path.exists():
        return []
    entries: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if isinstance(entry, dict) and "metric" in entry and "baseline" in entry:
            entries.append(entry)
    return entries


def append_ledger(entry: dict[str, Any], directory: Path | None = None) -> None:
    """Append one applied lever; ``date`` is filled in when missing."""
    directory = _root(directory)
    directory.mkdir(parents=True, exist_ok=True)
    record = {"date": datetime.now(tz=UTC).strftime("%Y-%m-%d"), **entry}
    with (directory / LEDGER_NAME).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")


@dataclass(frozen=True)
class Verdict:
    """How one applied lever turned out against the latest snapshot."""

    lever: str
    metric: str
    baseline: float
    predicted: float | None
    actual: float | None
    outcome: str
    note: str = ""


def _outcome(baseline: float, actual: float, *, lower_is_better: bool) -> str:
    """Classify a metric move as helped / no effect / regressed."""
    if not baseline:
        return "no baseline"
    change = (actual - baseline) / abs(baseline)
    if abs(change) <= NOISE:
        return "no effect"
    improved = change < 0 if lower_is_better else change > 0
    return "helped" if improved else "regressed"


def _prediction_note(baseline: float, predicted: float | None, actual: float) -> str:
    """Flag a prediction that missed the measured move by more than tolerance."""
    if predicted is None:
        return ""
    want = baseline - predicted
    got = baseline - actual
    if not want:
        return ""
    drift = abs(got - want) / abs(want)
    if drift <= PREDICTION_TOLERANCE:
        return "prediction held"
    return f"prediction off by {drift:.0%}"


def score(entries: list[dict[str, Any]], snap: dict[str, Any]) -> list[Verdict]:
    """Score each ledger entry against the snapshot's current metric values."""
    metrics = snap.get("metrics", {})
    verdicts: list[Verdict] = []
    for entry in entries:
        metric = str(entry["metric"])
        baseline = float(entry["baseline"])
        raw_predicted = entry.get("predicted")
        predicted = float(raw_predicted) if raw_predicted is not None else None
        value = metrics.get(metric)
        if not isinstance(value, (int, float)):
            verdicts.append(
                Verdict(
                    str(entry.get("lever", "?")),
                    metric,
                    baseline,
                    predicted,
                    None,
                    "unmeasured",
                    "metric absent from snapshot",
                ),
            )
            continue
        actual = float(value)
        lower = bool(entry.get("lower_is_better", True))
        verdicts.append(
            Verdict(
                lever=str(entry.get("lever", "?")),
                metric=metric,
                baseline=baseline,
                predicted=predicted,
                actual=actual,
                outcome=_outcome(baseline, actual, lower_is_better=lower),
                note=_prediction_note(baseline, predicted, actual),
            ),
        )
    return verdicts
