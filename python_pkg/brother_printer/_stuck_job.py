"""Detect a print job that CUPS calls "processing" but that is going nowhere.

Two failure modes seen on the HL-1110 (2026-10-12), neither visible in
``printer-state-reasons``:

* **Stalled job** - the printer failed to pick up paper. It raises the
  paper-empty bit, the ``usb://`` backend blocks, and CUPS keeps saying
  "processing". Only the job's page counter freezes.
* **Orphaned backend** - ``cancel`` removes the job but the blocked backend
  survives, so the queue stays "now printing <queue>-0" forever and even
  ``systemctl restart cups`` hangs. Killing the backend is the only cure.

``job-impressions-completed`` counts pages the filters have *rasterised*, not
sheets out of the printer: it runs ~5 pages ahead of the paper. That is fine
for spotting a freeze, useless as "pages printed".
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
import shutil
import signal
import time
from typing import TYPE_CHECKING

from python_pkg.brother_printer._query import run_command_text
from python_pkg.brother_printer.constants import (
    DERIVED_BACKEND_ORPHANED,
    DERIVED_JOB_STALLED,
    DIM,
    GREEN,
    RED,
    RESET,
    _out,
    _prompt,
)

if TYPE_CHECKING:
    from python_pkg.brother_printer.data_classes import USBResult

# A healthy run on 2026-10-12 froze the counter for up to ~9 s between pages
# (sampled every 3 s), so 15 s leaves headroom before calling it stalled.
STALL_WINDOW_SEC = 15.0
POLL_INTERVAL_SEC = 1.0
PROC_DIR = Path("/proc")
_BACKEND_PREFIX = "usb://Brother"
_IMPRESSIONS_RE = re.compile(r"job-impressions-completed \(integer\) = (\d+)")


@dataclass
class StuckJob:
    """A job (or its leftover backend) that is not making progress."""

    kind: str  # "stalled" or "orphaned"
    job_id: str
    backend_pid: int = 0


def find_backend_pids() -> dict[str, int]:
    """Map CUPS job id -> PID of every running Brother ``usb://`` backend."""
    backends: dict[str, int] = {}
    for entry in PROC_DIR.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            argv = (entry / "cmdline").read_bytes().split(b"\0")
        except OSError:
            continue  # process exited mid-scan, or not ours to read
        # cmdline is NUL-terminated, so argv[1] is b"" when there is no job id.
        if (
            len(argv) > 1
            and argv[1]
            and argv[0].decode(errors="replace").startswith(_BACKEND_PREFIX)
        ):
            backends[argv[1].decode(errors="replace")] = int(entry.name)
    return backends


def _job_impressions(job_id: str) -> int | None:
    """Read a job's rasterised-page counter, or None if CUPS will not say."""
    ipptool_path = shutil.which("ipptool")
    if not ipptool_path:
        return None
    uri = f"ipp://localhost/jobs/{job_id}"
    output = run_command_text([ipptool_path, "-tv", uri, "get-job-attributes.test"])
    match = _IMPRESSIONS_RE.search(output)
    return int(match.group(1)) if match else None


def _job_is_stalled(job_id: str) -> bool:
    """Watch the page counter; True if it does not move within the window."""
    start = _job_impressions(job_id)
    if start is None:
        return False
    deadline = time.monotonic() + STALL_WINDOW_SEC
    while time.monotonic() < deadline:
        time.sleep(POLL_INTERVAL_SEC)
        if _job_impressions(job_id) != start:
            return False
    return True


def detect_stuck_job(active_job_ids: list[str]) -> StuckJob | None:
    """Find an orphaned backend or a stalled active job.

    Args:
        active_job_ids: numeric ids of the jobs CUPS still lists for the queue.
    """
    backends = find_backend_pids()
    for job_id, pid in sorted(backends.items()):
        if job_id not in active_job_ids:
            return StuckJob("orphaned", job_id, pid)
    if active_job_ids and _job_is_stalled(active_job_ids[0]):
        job_id = active_job_ids[0]
        return StuckJob("stalled", job_id, backends.get(job_id, 0))
    return None


def kill_backend(pid: int) -> bool:
    """SIGKILL a hung backend; SIGTERM is what it already ignored."""
    try:
        os.kill(pid, signal.SIGKILL)
    except OSError:
        return False
    return True


def offer_backend_kill(pid: int) -> None:
    """Ask before killing an orphaned backend; nothing else unblocks the queue."""
    _out()
    choice = _prompt(f"  Kill hung backend PID {pid} to unblock the queue? [y/N]: ")
    if choice.strip().lower() != "y":
        _out(f"  {DIM}No changes made.{RESET}")
    elif kill_backend(pid):
        _out(f"  {GREEN}✓ Backend killed. CUPS will return to idle.{RESET}")
    else:
        _out(f"  {RED}Could not kill PID {pid} (already gone, or not root).{RESET}")


def _active_job_ids(printer_name: str) -> list[str]:
    """Numeric ids of the jobs CUPS still lists for the queue."""
    lpstat_path = shutil.which("lpstat")
    if not lpstat_path:
        return []
    output = run_command_text([lpstat_path, "-o", printer_name])
    prefix = f"{printer_name}-"
    return [
        line.split()[0].removeprefix(prefix)
        for line in output.splitlines()
        if line.startswith(prefix)
    ]


def flag_stuck_job(result: USBResult, printer_name: str) -> bool:
    """Replace a misleading "printing" status when the job is going nowhere."""
    stuck = detect_stuck_job(_active_job_ids(printer_name))
    if stuck is None:
        return False
    result.online = "TRUE"
    if stuck.kind == "orphaned":
        result.status_code = DERIVED_BACKEND_ORPHANED
        result.display = (
            f"backend PID {stuck.backend_pid} of cancelled job {stuck.job_id}"
            ' still running (a leftover "filter failed" message is just'
            " the cancel killing Ghostscript)"
        )
        result.cups.orphaned_backend_pid = stuck.backend_pid
    else:
        result.status_code = DERIVED_JOB_STALLED
        result.display = f"job {stuck.job_id} has not advanced a page in 15 s"
    return True
