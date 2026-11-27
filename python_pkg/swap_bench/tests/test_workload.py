"""Tests for the seeded swap-pressure workload.

Sizes stay at a few MiB: the anonymous mapping is real memory, but far too
small to push anything into swap, so the tests check determinism and the
output contract, not kernel behaviour.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from python_pkg.swap_bench.workload import PAGE, Spec, build_pool, run

if TYPE_CHECKING:
    from pathlib import Path


def test_pool_is_seeded_and_page_sized() -> None:
    """Same seed gives the same pool; every template is one page."""
    a = build_pool(seed=7, pool_pages=64, random_share=0.25)
    b = build_pool(seed=7, pool_pages=64, random_share=0.25)
    assert a == b
    assert len(a) == 64
    assert all(len(p) == PAGE for p in a)
    assert build_pool(seed=8, pool_pages=64, random_share=0.25) != a


def test_pool_random_share_controls_random_pages() -> None:
    """random_share=0 yields only text pages; 1 yields only random ones."""
    text = build_pool(seed=1, pool_pages=16, random_share=0.0)
    assert all(p.rstrip(b" ").replace(b" ", b"").isalpha() for p in text)
    rand = build_pool(seed=1, pool_pages=16, random_share=1.0)
    assert not any(p.replace(b" ", b"").isalpha() for p in rand)


def test_run_is_deterministic() -> None:
    """Two runs with one spec report identical pages and checksums (C7)."""
    spec = Spec(size_mib=2, seed=42, pool_pages=32, rounds=2)
    first, second = run(spec), run(spec)
    assert first.pages == second.pages == 2 * 256
    assert first.fill_crc == second.fill_crc
    assert first.touch_crc == second.touch_crc
    assert first.majflt >= 0
    assert first.seconds >= 0


def test_run_seed_changes_checksum() -> None:
    """A different seed is a different workload."""
    a = run(Spec(size_mib=1, seed=1, pool_pages=16, rounds=1))
    b = run(Spec(size_mib=1, seed=2, pool_pages=16, rounds=1))
    assert a.fill_crc != b.fill_crc


def test_run_handles_partial_last_chunk() -> None:
    """A page count that is not a chunk multiple is still filled fully."""
    spec = Spec(size_mib=1, seed=3, pool_pages=8, rounds=1, chunk_pages=100)
    assert run(spec).pages == 256


def test_spec_rejects_bad_values() -> None:
    """Non-positive sizes and shares outside [0, 1] are refused."""
    with pytest.raises(ValueError, match="size_mib"):
        Spec(size_mib=0, seed=1)
    with pytest.raises(ValueError, match="hot_share"):
        Spec(size_mib=1, seed=1, hot_share=1.5)
    with pytest.raises(ValueError, match="random_share"):
        Spec(size_mib=1, seed=1, random_share=-0.1)


def test_run_copies_snapshots_while_mapped(tmp_path: Path) -> None:
    """Snapshots are copied during the run, creating the destination dir."""
    src = tmp_path / "src"
    src.write_text("zswap 7\n")
    dest = tmp_path / "peak" / "memory.stat"
    run(Spec(size_mib=1, seed=1, pool_pages=8, rounds=1), [(src, dest)])
    assert dest.read_text() == "zswap 7\n"
