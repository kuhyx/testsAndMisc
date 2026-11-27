"""Tests for turning one run's raw /proc and /sys copies into a TSV row."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from python_pkg.swap_bench.stats import COLUMNS, compute_row, format_row

if TYPE_CHECKING:
    from pathlib import Path


def _row(run_dir: Path, env: str, setup: str) -> dict[str, str]:
    return compute_row(run_dir, env=env, setup=setup, seed=1, size_mib=1, date="d")


def test_zram_host_row(run_dir: Path) -> None:
    """Host zram: scope PSI, per-run mm_stat ratio, zram writes not disk."""
    row = _row(run_dir, "host", "zram")
    assert row["ratio"] == "3.00"  # (4-1) GiB in over (1.5-0.5) GiB stored
    assert row["psi_some_ms"] == "40"
    assert row["psi_full_ms"] == "30"
    assert row["majflt"] == "500"
    # 8000 pswpout pages minus (65600-8000)/8 = 7200 zram pages.
    assert row["disk_wb_pages"] == "800"
    assert row["zswpwb"] == "3"
    assert row["global_full_avg10"] == "0.20"
    assert row["pages"] == "256"
    assert row["desktop_full_ms"] == "6"  # two sessions, 3000 us each
    # Global pswpout grew 8000 pages, the scope swapped out 7000.
    assert row["outside_pswpout"] == "1000"
    assert list(row) == list(COLUMNS)


def test_zswap_host_ratio_from_cgroup(run_dir: Path) -> None:
    """Host zswap: ratio from the scope's zswapped/zswap at peak."""
    assert _row(run_dir, "host", "zswap")["ratio"] == "3.50"


def test_vm_rows_are_system_wide(run_dir: Path) -> None:
    """VM: global PSI and zswpwb deltas, ratio from /proc/meminfo."""
    row = _row(run_dir, "vm", "zswap")
    assert row["psi_some_ms"] == "300"
    assert row["psi_full_ms"] == "200"
    assert row["zswpwb"] == "2"
    assert row["ratio"] == "2.50"
    assert row["desktop_full_ms"] == "na"
    assert row["outside_pswpout"] == "na"


def test_host_without_sessions_has_no_desktop_psi(run_dir: Path) -> None:
    """No login session scope (a headless host) gives na, not zero."""
    (run_dir / "before/desktop_pressure").unlink()
    assert _row(run_dir, "host", "zram")["desktop_full_ms"] == "na"


def test_missing_zram_files_mean_no_zram(run_dir: Path) -> None:
    """Without zram stats, every pswpout page counts as disk writeback."""
    for name in (
        "before/zram_stat",
        "after/zram_stat",
        "before/mm_stat",
        "peak/mm_stat",
    ):
        (run_dir / name).unlink()
    row = _row(run_dir, "vm", "zram")
    assert row["disk_wb_pages"] == "8000"
    assert row["ratio"] == "na"


def test_zero_pool_ratio_is_na(run_dir: Path) -> None:
    """A run that never reached the pool has no ratio, not a crash."""
    (run_dir / "peak/meminfo").write_text("Zswap: 0 kB\nZswapped: 0 kB\n")
    assert _row(run_dir, "vm", "zswap")["ratio"] == "na"


def test_bad_env_is_refused(run_dir: Path) -> None:
    """Only host and vm exist."""
    with pytest.raises(ValueError, match="env"):
        _row(run_dir, "cloud", "zram")


def test_format_row_is_tab_separated(run_dir: Path) -> None:
    """format_row joins the columns in order with tabs."""
    row = _row(run_dir, "host", "zram")
    assert format_row(row) == "\t".join(row[c] for c in COLUMNS)
    assert format_row(None) == "\t".join(COLUMNS)
