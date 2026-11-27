"""Fill anonymous memory with seeded pages, then re-touch a hot subset.

Every byte depends on the seed alone (no file contents, no clock), so the
same seed is the same workload on the host and in a guest, on any day. The
page mix compresses about 3.4:1 under zstd: Zipf-weighted text from a
64-word seeded vocabulary, plus a share of incompressible random pages.
"""

from __future__ import annotations

from bisect import bisect
from dataclasses import dataclass
from itertools import accumulate
import mmap
import resource
import string
import time
from typing import TYPE_CHECKING
import zlib

from python_pkg.swap_bench.seeded import stream_bytes, stream_u32

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

PAGE = 4096
_VOCAB_WORDS = 64
_WORDS_PER_PAGE = 900  # comfortably more than one page of text
_U32 = 1 << 32


@dataclass(frozen=True)
class Spec:
    """One workload: how much memory, which seed, how hot the re-touch is."""

    size_mib: int
    seed: int
    random_share: float = 0.05
    hot_share: float = 0.25
    rounds: int = 3
    pool_pages: int = 1024
    chunk_pages: int = 64

    def __post_init__(self) -> None:
        """Refuse specs that would make an empty or undefined workload."""
        for name in ("size_mib", "rounds", "pool_pages", "chunk_pages"):
            if getattr(self, name) <= 0:
                msg = f"{name} must be positive"
                raise ValueError(msg)
        for name in ("random_share", "hot_share"):
            if not 0.0 <= getattr(self, name) <= 1.0:
                msg = f"{name} must be within [0, 1]"
                raise ValueError(msg)


@dataclass(frozen=True)
class Result:
    """What one run did; identical across runs of one spec except timing."""

    pages: int
    fill_crc: int
    touch_crc: int
    majflt: int
    seconds: float


def build_pool(seed: int, pool_pages: int, random_share: float) -> list[bytes]:
    """Return ``pool_pages`` seeded page templates, ``random_share`` random."""
    lengths = stream_u32(seed, "word-length", _VOCAB_WORDS)
    letters = stream_bytes(seed, "word-letters", _VOCAB_WORDS * 10)
    vocab = [
        "".join(
            string.ascii_lowercase[c % 26]
            for c in letters[w * 10 : w * 10 + 3 + lengths[w] % 8]
        )
        for w in range(_VOCAB_WORDS)
    ]
    cumulative = list(accumulate(1 / (rank + 1) for rank in range(_VOCAB_WORDS)))
    scale = cumulative[-1] / _U32
    n_random = round(pool_pages * random_share)
    pool = [stream_bytes(seed, f"random-page-{i}", PAGE) for i in range(n_random)]
    for i in range(pool_pages - n_random):
        draws = stream_u32(seed, f"text-page-{i}", _WORDS_PER_PAGE)
        text = " ".join(vocab[bisect(cumulative, d * scale)] for d in draws)
        pool.append(text.encode()[:PAGE])
    keys = stream_u32(seed, "shuffle", pool_pages)
    return [pool[i] for i in sorted(range(pool_pages), key=keys.__getitem__)]


def _fill(buf: mmap.mmap, spec: Spec, pool: list[bytes]) -> int:
    """Write every page of ``buf`` from the pool; return the data CRC."""
    pages = len(buf) // PAGE
    picks = stream_u32(spec.seed, "fill", pages)
    crc = 0
    for first in range(0, pages, spec.chunk_pages):
        count = min(spec.chunk_pages, pages - first)
        chunk = b"".join(
            pool[picks[j] % len(pool)] for j in range(first, first + count)
        )
        buf[first * PAGE : (first + count) * PAGE] = chunk
        crc = zlib.crc32(chunk, crc)
    return crc


def _touch(buf: mmap.mmap, spec: Spec) -> int:
    """Read a seeded hot subset ``rounds`` times; return the read CRC.

    Each page is hot with probability ``hot_share``; hot pages are visited in
    the order of their seeded key, i.e. a fixed random order.
    """
    pages = len(buf) // PAGE
    keys = stream_u32(spec.seed, "hot", pages)
    limit = spec.hot_share * _U32
    hot = sorted((k, i) for i, k in enumerate(keys) if k < limit)
    crc = 0
    for _ in range(spec.rounds):
        for _key, page in hot:
            crc = zlib.crc32(buf[page * PAGE : (page + 1) * PAGE], crc)
    return crc


def run(spec: Spec, snapshots: Sequence[tuple[Path, Path]] = ()) -> Result:
    """Run one workload in a fresh anonymous mapping.

    Each ``(src, dest)`` in ``snapshots`` is copied after the touch phase,
    while the mapping is still live: that is when the zram/zswap pool holds
    this run's pages, so its compression ratio can be read.
    """
    pool = build_pool(spec.seed, spec.pool_pages, spec.random_share)
    start_flt = resource.getrusage(resource.RUSAGE_SELF).ru_majflt
    start = time.monotonic()
    with mmap.mmap(-1, spec.size_mib * 1024 * 1024) as buf:
        fill_crc = _fill(buf, spec, pool)
        touch_crc = _touch(buf, spec)
        for src, dest in snapshots:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(src.read_bytes())
        pages = len(buf) // PAGE
    return Result(
        pages=pages,
        fill_crc=fill_crc,
        touch_crc=touch_crc,
        majflt=resource.getrusage(resource.RUSAGE_SELF).ru_majflt - start_flt,
        seconds=round(time.monotonic() - start, 3),
    )
