"""Per-setup medians of a results TSV and the agreed winner rule.

Rule (kuhy, 2026-11-27): lower PSI ``full`` wins; major faults break a tie;
a difference under 10 % (the run-to-run noise) is a tie, and a tie on both
keeps zram, the incumbent.
"""

from __future__ import annotations

import csv
from statistics import median
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

NOISE = 0.10
_METRICS = ("ratio", "psi_some_ms", "psi_full_ms", "majflt", "disk_wb_pages", "zswpwb")


def _differs(a: float, b: float) -> bool:
    top = max(a, b)
    return top > 0 and abs(a - b) / top >= NOISE


def pick_winner(zram: dict[str, float], zswap: dict[str, float]) -> tuple[str, str]:
    """Return ``(winner, reason)`` from the two setups' medians."""
    for key, label in (("psi_full_ms", "PSI full"), ("majflt", "major faults")):
        if _differs(zram[key], zswap[key]):
            winner = "zram" if zram[key] < zswap[key] else "zswap"
            return (
                winner,
                f"lower median {label} ({zram[key]:g} zram vs {zswap[key]:g} zswap)",
            )
    return "zram", "PSI full and major faults within 10 %: the incumbent stays"


def _medians(rows: list[dict[str, str]]) -> dict[str, float]:
    out: dict[str, float] = {}
    for key in _METRICS:
        values = [float(r[key]) for r in rows if r[key] != "na"]
        out[key] = median(values) if values else float("nan")
    return out


def summarize(path: Path) -> str:
    """Markdown table of medians per env and setup, then one winner line per env."""
    with path.open(newline="") as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))
    groups: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in rows:
        groups.setdefault((row["env"], row["setup"]), []).append(row)
    titles = ("env", "setup", "runs", "ratio", "PSI some ms", "PSI full ms")
    titles += ("major faults", "disk writeback pages", "zswap writeback")
    lines = ["| " + " | ".join(titles) + " |", "|---" * len(titles) + "|"]
    medians: dict[tuple[str, str], dict[str, float]] = {}
    for (env, setup), members in sorted(groups.items()):
        med = medians[env, setup] = _medians(members)
        cells = [env, setup, str(len(members)), f"{med['ratio']:.2f}"]
        cells += [f"{med[key]:g}" for key in _METRICS[1:]]
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")
    for env in sorted({env for env, _ in groups}):
        if (env, "zram") in medians and (env, "zswap") in medians:
            winner, reason = pick_winner(medians[env, "zram"], medians[env, "zswap"])
            lines.append(f"{env} winner: {winner}: {reason}")
        else:
            lines.append(f"{env} winner: n/a (needs runs of both setups)")
    return "\n".join(lines) + "\n"
