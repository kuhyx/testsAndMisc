"""Deterministic byte and integer streams from a seed.

``random.Random`` would do, but the repo's lint (S311) refuses it outright;
SHAKE-256 gives the same reproducibility, in bulk, from the standard library.
Every stream is named by a label, so adding a stream never shifts another.
"""

from __future__ import annotations

import array
import hashlib


def stream_bytes(seed: int, label: str, n: int) -> bytes:
    """Return ``n`` bytes fixed by ``seed`` and ``label``."""
    return hashlib.shake_256(f"{seed}/{label}".encode()).digest(n)


def stream_u32(seed: int, label: str, n: int) -> array.array[int]:
    """Return ``n`` unsigned 32-bit ints fixed by ``seed`` and ``label``."""
    out = array.array("I")  # 4 bytes on every Linux target this runs on
    out.frombytes(stream_bytes(seed, label, n * out.itemsize))
    return out
