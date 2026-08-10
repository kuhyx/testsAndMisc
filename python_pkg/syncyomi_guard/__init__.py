"""Integrity guard for the SyncYomi server's library payload.

TachiyomiSY 1.13.2 has an open upstream bug (jobobby04/TachiyomiSY#1634, #1638)
where a backup restore fails with ``SQLITE_BUSY`` on the app's *own* database.
The loud failure is survivable. The dangerous case is the quiet one: a restore
that reports ``Worker result SUCCESS`` while having written almost nothing, and
then pushes that near-empty library up to the server, replacing the only good
copy.

That happened on 2026-08-09: a 14 MB payload holding 2182 manga became a 267 KB
stub holding only sources and settings, and the real library survived solely as
stale pages in the SQLite write-ahead log.

This package exists so that never depends on luck again. It decodes the payload,
counts what is actually in it, and refuses to accept a collapse as normal. It
cannot prevent the upstream bug — that is Kotlin code in an APK — so it aims at
the part that is actually fixable: never letting a degraded copy become the only
copy.
"""

from __future__ import annotations

from python_pkg.syncyomi_guard.payload import (
    PayloadError,
    PayloadStats,
    decode_payload,
)
from python_pkg.syncyomi_guard.verdict import (
    Thresholds,
    Verdict,
    compare,
)

__all__ = [
    "PayloadError",
    "PayloadStats",
    "Thresholds",
    "Verdict",
    "compare",
    "decode_payload",
]
