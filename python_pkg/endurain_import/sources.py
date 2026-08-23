"""Where activity files come from.

Primary source is the WebDAV inbox the phone uploads into. The adb fallback
exists because RunnerUp has no background sync -- uploads only happen when the
user taps the upload button -- so a run can sit on the phone indefinitely. When
the phone is attached, its export directory is pulled into the same inbox and
from there follows the identical path, deduplicated by content hash.

This module is strictly read-only with respect to the phone. screen-locker's
workout verification reads the same directory over adb and is the gate that
unlocks the PC; nothing here may delete, move, or rewrite those files.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

_logger = logging.getLogger(__name__)

# RunnerUp's File synchronizer target on the phone.
PHONE_EXPORT_DIR = "/sdcard/Documents/RunnerUp"
ACTIVITY_SUFFIXES = (".tcx", ".gpx", ".fit")
_ADB_TIMEOUT = 60
# Resolved at call time so a missing adb is reported as "no device" rather than
# crashing the whole import run.
_ADB_BIN = shutil.which("adb") or "adb"


def inbox_files(inbox: Path) -> list[Path]:
    """Return activity files waiting in the WebDAV inbox, oldest first.

    ``processed/`` is skipped: it holds files this importer has already
    delivered and is not rescanned.
    """
    if not inbox.is_dir():
        return []
    found = [
        path
        for path in inbox.iterdir()
        if path.is_file() and path.suffix.lower() in ACTIVITY_SUFFIXES
    ]
    return sorted(found, key=lambda p: p.stat().st_mtime)


def _adb(args: list[str]) -> tuple[bool, str]:
    """Run an adb command, returning (ok, output)."""
    try:
        proc = subprocess.run(
            [_ADB_BIN, *args],
            capture_output=True,
            text=True,
            timeout=_ADB_TIMEOUT,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)
    return proc.returncode == 0, proc.stdout + proc.stderr


def phone_attached() -> bool:
    """True when exactly one adb device is in the 'device' state."""
    ok, out = _adb(["devices"])
    if not ok:
        return False
    states = [
        line.split("\t")[1].strip() for line in out.splitlines()[1:] if "\t" in line
    ]
    return "device" in states


def pull_from_phone(inbox: Path) -> list[Path]:
    """Copy RunnerUp exports from the phone into ``inbox``.

    Returns the paths newly written. Files already present in the inbox are
    left alone; content-level deduplication happens later against the ledger,
    so a name collision here is not authoritative either way.
    """
    if not phone_attached():
        _logger.info("no adb device attached; skipping phone fallback")
        return []

    ok, out = _adb(["shell", "ls", PHONE_EXPORT_DIR])
    if not ok:
        _logger.warning("could not list %s: %s", PHONE_EXPORT_DIR, out.strip())
        return []

    names = [
        line.strip()
        for line in out.splitlines()
        if line.strip().lower().endswith(ACTIVITY_SUFFIXES)
    ]
    inbox.mkdir(parents=True, exist_ok=True)
    pulled: list[Path] = []
    for name in names:
        target = inbox / name
        if target.exists():
            continue
        staged = inbox / f".{name}.partial"
        ok, err = _adb(["pull", f"{PHONE_EXPORT_DIR}/{name}", str(staged)])
        if not ok:
            _logger.warning("adb pull failed for %s: %s", name, err.strip())
            staged.unlink(missing_ok=True)
            continue
        # Rename only after a complete pull, so a partial transfer is never
        # picked up as a whole activity by this or any concurrent run.
        shutil.move(str(staged), str(target))
        pulled.append(target)

    if pulled:
        _logger.info("pulled %d file(s) from the phone", len(pulled))
    return pulled
