"""Fixture trees of the raw files swap_bench.sh copies for one run."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

_PSI = (
    "some avg10=0.00 avg60=0.00 avg300=0.00 total={some}\n"
    "full avg10={f10} avg60=0.00 avg300=0.00 total={full}\n"
)


def _write(root: Path, name: str, text: str) -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


@pytest.fixture
def run_dir(tmp_path: Path) -> Path:
    """A zram run: 3 GiB in, 1 GiB compressed, 800 pages to disk."""
    gib = 1 << 30
    _write(
        tmp_path,
        "workload.txt",
        "pages=256\nfill_crc=11\ntouch_crc=22\nmajflt=500\nseconds=12.5\n",
    )
    _write(tmp_path, "before/vmstat", "pswpout 1000\nzswpwb 5\npgmajfault 9\n")
    _write(tmp_path, "after/vmstat", "pswpout 9000\nzswpwb 7\npgmajfault 9\n")
    _write(tmp_path, "before/zram_stat", "1 0 0 0 1 0 8000 0 0 0 0\n")
    _write(tmp_path, "after/zram_stat", "1 0 0 0 1 0 65600 0 0 0 0\n")
    _write(tmp_path, "before/mm_stat", f"{gib} {gib // 2} 0 0\n")
    _write(tmp_path, "peak/mm_stat", f"{4 * gib} {gib + gib // 2} 0 0\n")
    _write(tmp_path, "before/pressure", _PSI.format(some=1000, full=500, f10="0.10"))
    _write(
        tmp_path, "after/pressure", _PSI.format(some=301000, full=200500, f10="0.20")
    )
    _write(
        tmp_path,
        "before/desktop_pressure",
        2 * _PSI.format(some=0, full=1000, f10="0.00"),
    )
    _write(
        tmp_path,
        "after/desktop_pressure",
        2 * _PSI.format(some=0, full=4000, f10="0.00"),
    )
    _write(tmp_path, "cg_pressure", _PSI.format(some=40000, full=30000, f10="1.00"))
    _write(tmp_path, "cg_memory.stat", "zswpwb 3\nzswap 100\nzswapped 400\n")
    _write(tmp_path, "peak/memory.stat", "zswap 1000\nzswapped 3500\n")
    _write(
        tmp_path,
        "peak/meminfo",
        "MemTotal: 100 kB\nZswap:     200 kB\nZswapped:   500 kB\n",
    )
    return tmp_path
