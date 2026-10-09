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
import os
import shutil
import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

_logger = logging.getLogger(__name__)

# RunnerUp's File synchronizer target on the phone.
PHONE_EXPORT_DIR = "/sdcard/Documents/RunnerUp"
ACTIVITY_SUFFIXES = (".tcx", ".gpx", ".fit")
# Subdirectory of the inbox that holds files already delivered to Endurain.
PROCESSED_DIRNAME = "processed"
_ADB_TIMEOUT = 60
# Pins which phone to pull from when more than one device is attached. Without
# it every adb call fails with "more than one device/emulator" -- silently, as
# a warning on the fallback path -- the moment a second device (a spare handset,
# an emulator) shows up. Left unset the single attached device is used.
ADB_SERIAL_ENV = "ENDURAIN_ADB_SERIAL"
# Resolved at call time so a missing adb is reported as "no device" rather than
# crashing the whole import run.
_ADB_BIN = shutil.which("adb") or "adb"


def processed_dir_for(inbox: Path) -> Path:
    """Return where ``inbox`` keeps files this importer has already delivered.

    Single definition shared by the importer (which moves files there) and the
    phone fallback (which must not pull them back out of the phone again).
    """
    return inbox / PROCESSED_DIRNAME


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


def _adb(args: list[str], serial: str | None = None) -> tuple[bool, str]:
    """Run an adb command, returning (ok, output).

    ``serial`` is threaded into the argv as ``-s`` so every call targets one
    named device. Omitting it is only correct for ``devices`` itself, which is
    what resolves the serial in the first place.
    """
    prefix = ["-s", serial] if serial else []
    try:
        proc = subprocess.run(
            [_ADB_BIN, *prefix, *args],
            capture_output=True,
            text=True,
            timeout=_ADB_TIMEOUT,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)
    return proc.returncode == 0, proc.stdout + proc.stderr


def attached_serials() -> list[str]:
    """Return the serials of every device in the 'device' state."""
    ok, out = _adb(["devices"])
    if not ok:
        return []
    serials = []
    for line in out.splitlines()[1:]:
        if "\t" not in line:
            continue
        serial, state = line.split("\t", 1)
        if state.strip() == "device":
            serials.append(serial.strip())
    return serials


def resolve_serial() -> str | None:
    """Pick the phone to pull from, or None when the choice is not clear.

    Ambiguity is resolved by configuration, never by guessing: with several
    devices attached and no ``ENDURAIN_ADB_SERIAL`` set, this returns None so
    the fallback is skipped outright. The alternative -- letting bare adb pick
    -- is what produced "more than one device/emulator" as a warning on a path
    nobody watches.
    """
    pinned = os.environ.get(ADB_SERIAL_ENV, "").strip()
    serials = attached_serials()
    if pinned:
        if pinned in serials:
            return pinned
        _logger.warning(
            "%s=%s is set but that device is not attached (attached: %s)",
            ADB_SERIAL_ENV,
            pinned,
            ", ".join(serials) or "none",
        )
        return None
    if not serials:
        return None
    if len(serials) > 1:
        _logger.warning(
            "%d devices attached (%s); set %s to choose one. Skipping the "
            "phone fallback rather than pulling from an arbitrary device.",
            len(serials),
            ", ".join(serials),
            ADB_SERIAL_ENV,
        )
        return None
    return serials[0]


def pull_from_phone(inbox: Path) -> list[Path]:
    """Copy RunnerUp exports from the phone into ``inbox``.

    Returns the paths newly written. A file is skipped when its name already
    sits in the inbox (waiting to be imported) or in ``processed/`` (already
    imported). The phone keeps every export forever, so without the
    ``processed/`` check each run re-pulls the whole history into the inbox,
    where it re-triggers every inotify watcher on that directory. Content-level
    deduplication still happens later against the ledger.
    """
    serial = resolve_serial()
    if serial is None:
        _logger.info("no adb device selected; skipping phone fallback")
        return []

    ok, out = _adb(["shell", "ls", PHONE_EXPORT_DIR], serial)
    if not ok:
        _logger.warning("could not list %s: %s", PHONE_EXPORT_DIR, out.strip())
        return []

    names = [
        line.strip()
        for line in out.splitlines()
        if line.strip().lower().endswith(ACTIVITY_SUFFIXES)
    ]
    inbox.mkdir(parents=True, exist_ok=True)
    processed = processed_dir_for(inbox)
    pulled: list[Path] = []
    pending = imported = failed = 0
    for name in names:
        target = inbox / name
        if target.exists():
            pending += 1
            continue
        if (processed / name).exists():
            imported += 1
            continue
        staged = inbox / f".{name}.partial"
        ok, err = _adb(["pull", f"{PHONE_EXPORT_DIR}/{name}", str(staged)], serial)
        if not ok:
            _logger.warning("adb pull failed for %s: %s", name, err.strip())
            staged.unlink(missing_ok=True)
            failed += 1
            continue
        # Rename only after a complete pull, so a partial transfer is never
        # picked up as a whole activity by this or any concurrent run.
        shutil.move(str(staged), str(target))
        pulled.append(target)

    # Failed pulls are each reported above; the summary escalates too so a
    # partially broken fallback is visible in the one line people read.
    _logger.log(
        logging.WARNING if failed else logging.INFO,
        "phone fallback: %d on phone, %d pulled, %d skipped as already "
        "imported, %d skipped as already in the inbox, %d failed",
        len(names),
        len(pulled),
        imported,
        pending,
        failed,
    )
    return pulled
