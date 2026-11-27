"""Tests for the per-setup medians and the agreed winner rule."""

from __future__ import annotations

from typing import TYPE_CHECKING

from python_pkg.swap_bench.stats import COLUMNS
from python_pkg.swap_bench.summary import pick_winner, summarize

if TYPE_CHECKING:
    from pathlib import Path


def _tsv(tmp_path: Path, rows: list[tuple[str, str, str, str, str]]) -> Path:
    """Rows of (env, setup, psi_full_ms, majflt, ratio)."""
    lines = ["\t".join(COLUMNS)]
    for env, setup, full, majflt, ratio in rows:
        row = dict.fromkeys(COLUMNS, "0")
        row.update(env=env, setup=setup, psi_full_ms=full, majflt=majflt, ratio=ratio)
        lines.append("\t".join(row[c] for c in COLUMNS))
    path = tmp_path / "r.tsv"
    path.write_text("\n".join(lines) + "\n")
    return path


def test_lower_psi_full_wins() -> None:
    """PSI full decides when it differs by 10% or more."""
    assert (
        pick_winner(
            {"psi_full_ms": 100, "majflt": 1}, {"psi_full_ms": 50, "majflt": 9}
        )[0]
        == "zswap"
    )
    assert (
        pick_winner(
            {"psi_full_ms": 50, "majflt": 9}, {"psi_full_ms": 100, "majflt": 1}
        )[0]
        == "zram"
    )


def test_majflt_breaks_a_psi_tie() -> None:
    """Under 10% PSI difference, major faults decide."""
    winner, reason = pick_winner(
        {"psi_full_ms": 100, "majflt": 1000}, {"psi_full_ms": 95, "majflt": 500}
    )
    assert winner == "zswap"
    assert "major faults" in reason


def test_double_tie_keeps_zram() -> None:
    """Under 10% on both, the incumbent zram stays."""
    winner, reason = pick_winner(
        {"psi_full_ms": 100, "majflt": 100}, {"psi_full_ms": 95, "majflt": 95}
    )
    assert winner == "zram"
    assert "incumbent" in reason


def test_zero_values_tie() -> None:
    """Both zero is a tie, not a division by zero."""
    assert (
        pick_winner({"psi_full_ms": 0, "majflt": 0}, {"psi_full_ms": 0, "majflt": 0})[0]
        == "zram"
    )


def test_summarize_medians_and_winner(tmp_path: Path) -> None:
    """Medians per env and setup, a winner line per env with both setups."""
    path = _tsv(
        tmp_path,
        [
            ("host", "zram", "100", "10", "3.00"),
            ("host", "zram", "300", "30", "3.20"),
            ("host", "zram", "200", "20", "na"),
            ("host", "zswap", "50", "10", "3.50"),
            ("vm", "zram", "10", "1", "3.00"),
        ],
    )
    text = summarize(path)
    assert "| host | zram | 3 | 3.10 |" in text
    assert "| 200 |" in text
    assert "host winner: zswap" in text
    assert "vm winner: n/a (needs runs of both setups)" in text
