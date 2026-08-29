"""Content-addressed record of what has already been imported.

Endurain has no duplicate detection: uploading the same file twice creates two
activities. The ledger is therefore the only thing standing between a re-run
and a duplicated activity history, and it keys on the file's SHA-256 rather
than its name so that the same run imports once even when it arrives by both
the WebDAV and adb routes under different filenames.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

_CHUNK = 1 << 20
# "RunnerUp", <timestamp>, <sport> -- the minimum for a parseable export name.
_MIN_NAME_PARTS = 3
# <yyyy>-<mm>-<dd>-<HH>-<MM>-<SS> once split on "-".
_STAMP_FIELDS = 6


class LedgerCorruptError(RuntimeError):
    """Raised when the on-disk ledger cannot be parsed."""


def activity_key(path: Path) -> str:
    """Return a stable identity for the *run*, independent of export format.

    RunnerUp writes the same activity as both .gpx and .tcx
    (RunnerUp_2026-08-22-23-51-04_Running.{gpx,tcx}). Those files have
    different bytes, so a content hash sees two distinct files and Endurain --
    which does no duplicate detection -- happily creates two activities for one
    run. Keying on the stem collapses them.

    The device model that RunnerUp's WebDAV synchronizer injects
    (RunnerUp_Pixel_6a_<ts>_Running) is stripped too, so the same run arriving
    over WebDAV and over adb resolves to one key.
    """
    stem = path.stem
    parts = stem.split("_")
    if len(parts) >= _MIN_NAME_PARTS and parts[0] == "RunnerUp":
        # Keep the trailing <timestamp>_<sport>; drop any model in between.
        return f"RunnerUp_{parts[-2]}_{parts[-1]}"
    return stem


def activity_start(path: Path) -> datetime | None:
    """Parse the run's start time out of a RunnerUp export filename.

    RunnerUp names exports with LOCAL wall-clock time
    (RunnerUp_2026-08-14-00-58-45_Running is 00:58 local, 22:58 UTC the day
    before), so the value is interpreted in the local zone and returned as
    UTC. Reading it as UTC directly would shift a late-evening run onto the
    wrong day and defeat the comparison it feeds.
    """
    key = activity_key(path)
    parts = key.split("_")
    if len(parts) < _MIN_NAME_PARTS:
        return None
    fields = parts[-2].split("-")
    if len(fields) != _STAMP_FIELDS:
        return None
    try:
        naive = datetime(
            int(fields[0]),
            int(fields[1]),
            int(fields[2]),
            int(fields[3]),
            int(fields[4]),
            int(fields[5]),
            tzinfo=datetime.now().astimezone().tzinfo,
        )
    except ValueError:
        return None
    return naive.astimezone(UTC)


def file_digest(path: Path) -> str:
    """Return the SHA-256 of ``path``, read incrementally."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(_CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class Entry:
    """One successfully imported file."""

    sha256: str
    activity_key: str
    filename: str
    activity_id: int | None
    uploaded_at: str

    def as_dict(self) -> dict[str, Any]:
        """Return the JSON-serialisable form stored in the ledger."""
        return {
            "activity_key": self.activity_key,
            "filename": self.filename,
            "activity_id": self.activity_id,
            "uploaded_at": self.uploaded_at,
        }


class Ledger:
    """A JSON-backed set of imported content hashes.

    Writes are atomic (temp file + replace) because the importer runs from a
    systemd timer: a crash mid-write must not leave a truncated ledger, which
    would look like "nothing has been imported" and duplicate the entire
    history on the next run.
    """

    def __init__(self, path: Path) -> None:
        """Open (or create) the ledger stored at ``path``."""
        self._path = path
        self._entries: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            raw = json.loads(self._path.read_text())
        except json.JSONDecodeError as exc:
            # Fail closed: a corrupt ledger must stop the run, not silently
            # re-import everything.
            message = f"corrupt ledger at {self._path}: {exc}"
            raise LedgerCorruptError(message) from exc
        if isinstance(raw, dict):
            self._entries = raw

    def __contains__(self, sha256: str) -> bool:
        """True when a file with this digest has already been imported."""
        return sha256 in self._entries

    def has_activity(self, key: str) -> bool:
        """True when this run was imported already, in any export format."""
        return any(entry.get("activity_key") == key for entry in self._entries.values())

    def __len__(self) -> int:
        """Number of files recorded as imported."""
        return len(self._entries)

    def record(self, entry: Entry) -> None:
        """Add ``entry`` and flush to disk immediately."""
        self._entries[entry.sha256] = entry.as_dict()
        self._flush()

    def _flush(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._entries, indent=2, sort_keys=True))
        tmp.replace(self._path)


def now_iso() -> str:
    """UTC timestamp for ledger entries."""
    return datetime.now(UTC).isoformat()
