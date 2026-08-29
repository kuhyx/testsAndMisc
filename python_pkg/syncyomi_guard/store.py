"""Read the live payload and keep versioned snapshots of the good ones.

Two rules shape this module, both learned on 2026-08-09:

* The database is opened **read-only**. The guard runs on a timer against a
  database a container is actively writing; it must never be the reason
  SyncYomi sees a lock.
* A snapshot is written only for a payload that passed. Snapshotting first and
  judging afterwards would have faithfully archived the 267 KB stub.

Snapshots are gzipped ``Backup`` messages, which is exactly the ``.tachibk``
format the app restores from — so recovery is "copy this file to the phone",
with no decoding step at the moment it is needed most.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
import gzip
import json
import sqlite3
from typing import TYPE_CHECKING, Final

from python_pkg.syncyomi_guard.payload import PayloadError, PayloadStats

if TYPE_CHECKING:
    from pathlib import Path

_STATE_FILENAME: Final = "last_known_good.json"

# The glob matches the timestamp layout *only*. A looser pattern such as
# ``syncyomi_*.tachibk`` would also match a hand-named file like
# ``syncyomi_recovered_2026-08-09.tachibk`` — the irreplaceable original
# rescued from the WAL — and the pruner would delete it as a stale snapshot.
_SNAPSHOT_GLOB: Final = "syncyomi_[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T*Z.tachibk"
_SNAPSHOT_STEM: Final = "syncyomi_%Y-%m-%dT%H-%M-%SZ"


class StoreError(RuntimeError):
    """Raised when the payload cannot be read from the SyncYomi database."""


def read_payload(db_path: Path) -> bytes:
    """Read the single ``sync_data`` blob from a SyncYomi SQLite database.

    Opened through an immutable URI: no locking, no WAL recovery, no write to
    the directory. The database stays exactly as the container left it.

    Raises:
        StoreError: If the database is unreadable or holds no sync row.
    """
    if not db_path.is_file():
        msg = f"no SyncYomi database at {db_path}"
        raise StoreError(msg)

    # ``sqlite3.connect`` as a context manager commits the transaction but does
    # NOT close the connection, so it is closed explicitly. A guard that leaks
    # handles against the live database would eventually become the thing
    # holding a file open on it.
    uri = f"file:{db_path}?immutable=1"
    try:
        conn = sqlite3.connect(uri, uri=True)
    except sqlite3.Error as exc:
        msg = f"cannot read {db_path}: {exc}"
        raise StoreError(msg) from exc

    try:
        rows = conn.execute(
            "SELECT data FROM sync_data ORDER BY id LIMIT 1",
        ).fetchall()
    except sqlite3.Error as exc:
        msg = f"cannot read {db_path}: {exc}"
        raise StoreError(msg) from exc
    finally:
        conn.close()

    if not rows:
        msg = f"{db_path} has no sync_data row"
        raise StoreError(msg)

    blob = rows[0][0]
    if not isinstance(blob, bytes):
        msg = f"sync_data.data is {type(blob).__name__}, expected bytes"
        raise StoreError(msg)
    return blob


def load_baseline(state_dir: Path) -> PayloadStats | None:
    """Load the last known good stats, or ``None`` when there is no baseline.

    A corrupt or partial state file is treated as absent rather than fatal: the
    guard then re-baselines loudly (``FIRST_RUN``) instead of refusing to run.
    """
    path = state_dir / _STATE_FILENAME
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return PayloadStats(
            size_bytes=int(raw["size_bytes"]),
            manga=int(raw["manga"]),
            categories=int(raw["categories"]),
            chapters=int(raw["chapters"]),
            sources=int(raw["sources"]),
        )
    except OSError, ValueError, KeyError, TypeError:
        return None


def save_baseline(state_dir: Path, stats: PayloadStats) -> Path:
    """Record ``stats`` as the new last known good baseline."""
    state_dir.mkdir(parents=True, exist_ok=True)
    path = state_dir / _STATE_FILENAME
    payload = dict(asdict(stats))
    payload["recorded_at"] = datetime.now(UTC).isoformat()
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def write_snapshot(
    snapshot_dir: Path,
    blob: bytes,
    keep: int,
    now: datetime | None = None,
) -> Path:
    """Write ``blob`` as a restorable ``.tachibk`` and prune old snapshots.

    Raises:
        ValueError: If ``keep`` is not at least 1.
    """
    if keep < 1:
        msg = f"keep must be >= 1, got {keep}"
        raise ValueError(msg)

    snapshot_dir.mkdir(parents=True, exist_ok=True)
    stamp = (now or datetime.now(UTC)).strftime(_SNAPSHOT_STEM)

    # Timestamps are second-granular, so two runs in the same second would map
    # to one filename and the second would silently overwrite the first —
    # quietly holding fewer than ``keep`` distinct snapshots, and in the worst
    # case replacing a good library with a stub written a fraction of a second
    # later. Suffix on collision rather than clobber.
    path = snapshot_dir / f"{stamp}.tachibk"
    suffix = 1
    while path.exists():
        path = snapshot_dir / f"{stamp}-{suffix}.tachibk"
        suffix += 1

    path.write_bytes(gzip.compress(blob))
    _prune(snapshot_dir, keep)
    return path


def _prune(snapshot_dir: Path, keep: int) -> None:
    """Delete all but the ``keep`` newest snapshots, by filename order.

    Filenames are UTC timestamps in a sortable layout, so lexical order is
    chronological order without stat-ing every file.
    """
    snapshots = sorted(snapshot_dir.glob(_SNAPSHOT_GLOB))
    for stale in snapshots[:-keep]:
        stale.unlink()


def latest_snapshot(snapshot_dir: Path) -> Path | None:
    """Return the newest snapshot, or ``None`` when none exist."""
    snapshots = sorted(snapshot_dir.glob(_SNAPSHOT_GLOB))
    return snapshots[-1] if snapshots else None


def read_snapshot(path: Path) -> bytes:
    """Decompress a ``.tachibk`` snapshot back into a raw payload.

    Raises:
        PayloadError: If the file is not readable gzip.
    """
    try:
        return gzip.decompress(path.read_bytes())
    except (OSError, gzip.BadGzipFile) as exc:
        msg = f"cannot read snapshot {path}: {exc}"
        raise PayloadError(msg) from exc
