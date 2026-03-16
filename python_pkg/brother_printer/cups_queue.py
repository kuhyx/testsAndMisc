"""CUPS queue inspection, display, and interactive fix functions."""

from __future__ import annotations

from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from typing import TYPE_CHECKING

from python_pkg.brother_printer.constants import (
    BOLD,
    CYAN,
    DIM,
    GREEN,
    MIN_LPSTAT_JOB_PARTS,
    RED,
    RESET,
    YELLOW,
    _out,
    _prompt,
)
from python_pkg.brother_printer.cups_service import find_cups_printer_name
from python_pkg.brother_printer.data_classes import CUPSJob, CUPSQueueStatus

if TYPE_CHECKING:
    from collections.abc import Callable


# ── Queue inspection ─────────────────────────────────────────────────


def _parse_lpstat_printer_line(line: str) -> tuple[bool, str]:
    """Parse an lpstat -p line. Returns (enabled, reason)."""
    enabled = "disabled" not in line.lower()
    reason = ""
    match = re.search(r"\d{4}\s+-\s*(.+)", line)
    if match:
        reason = match.group(1).strip()
    return enabled, reason


def _parse_lpstat_jobs(output: str, printer_name: str) -> list[CUPSJob]:
    """Parse lpstat -o output into CUPSJob list."""
    jobs: list[CUPSJob] = []
    for line in output.splitlines():
        if not line.startswith(printer_name):
            continue
        parts = line.split()
        if len(parts) >= MIN_LPSTAT_JOB_PARTS:
            job_id = parts[0]
            user = parts[1]
            size = parts[2]
            date = " ".join(parts[3:])
            jobs.append(CUPSJob(job_id=job_id, user=user, size=size, date=date))
    return jobs


def get_cups_queue_status() -> CUPSQueueStatus:
    """Check if the CUPS queue is disabled and list pending jobs."""
    printer_name = find_cups_printer_name()
    if not printer_name:
        return CUPSQueueStatus()

    result = CUPSQueueStatus(printer_name=printer_name)
    lpstat_path = shutil.which("lpstat")
    if not lpstat_path:
        return result

    try:
        r = subprocess.run(
            [lpstat_path, "-p", printer_name],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        for line in r.stdout.splitlines():
            if "printer" in line.lower() and printer_name in line:
                result.enabled, result.reason = _parse_lpstat_printer_line(line)
                break
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError):
        pass

    try:
        r = subprocess.run(
            [lpstat_path, "-o", printer_name],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        result.jobs = _parse_lpstat_jobs(r.stdout, printer_name)
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError):
        pass

    has_errors, last_error = _check_cups_backend_errors(printer_name)
    result.has_backend_errors = has_errors
    result.last_backend_error = last_error

    return result


# ── CUPS fix actions ─────────────────────────────────────────────────


def _cups_enable_printer(printer_name: str) -> bool:
    """Re-enable a disabled CUPS printer. Returns True on success."""
    cupsenable_path = shutil.which("cupsenable")
    if not cupsenable_path:
        _out(f"  {RED}cupsenable not found.{RESET}")
        return False
    try:
        subprocess.run(
            [cupsenable_path, printer_name],
            timeout=5,
            check=True,
        )
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, OSError) as e:
        _out(f"  {RED}Failed to enable printer: {e}{RESET}")
        return False
    else:
        return True


def _cups_cancel_all_jobs(printer_name: str) -> bool:
    """Cancel all pending jobs. Returns True on success."""
    cancel_path = shutil.which("cancel")
    if not cancel_path:
        _out(f"  {RED}cancel command not found.{RESET}")
        return False
    try:
        subprocess.run(
            [cancel_path, "-a", printer_name],
            timeout=5,
            check=True,
        )
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, OSError) as e:
        _out(f"  {RED}Failed to cancel jobs: {e}{RESET}")
        return False
    else:
        return True


def _cups_cancel_job(job_id: str) -> bool:
    """Cancel a specific job. Returns True on success."""
    cancel_path = shutil.which("cancel")
    if not cancel_path:
        return False
    try:
        subprocess.run(
            [cancel_path, job_id],
            timeout=5,
            check=True,
        )
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, OSError):
        return False
    else:
        return True


def _cups_restart_service() -> bool:
    """Restart the CUPS service. Returns True on success."""
    systemctl_path = shutil.which("systemctl")
    if not systemctl_path:
        _out(f"  {RED}systemctl not found.{RESET}")
        return False
    sys.stdout.write(f"  {DIM}Restarting CUPS...{RESET}")
    sys.stdout.flush()
    try:
        proc = subprocess.Popen(
            [systemctl_path, "restart", "cups"],
        )
        deadline = time.time() + 30
        while proc.poll() is None:
            if time.time() > deadline:
                proc.kill()
                proc.wait()
                sys.stdout.write("\n")
                _out(
                    f"  {RED}CUPS restart timed out"
                    f" (stuck backend process?).{RESET}"
                )
                _out(
                    f"  {DIM}Try: sudo kill -9 $(pgrep -f 'cups/backend/usb')"
                    f" && sudo systemctl restart cups{RESET}"
                )
                return False
            sys.stdout.write(".")
            sys.stdout.flush()
            time.sleep(1)
        sys.stdout.write("\n")
        if proc.returncode != 0:
            _out(
                f"  {RED}CUPS restart failed" f" (exit code {proc.returncode}).{RESET}"
            )
            return False
    except OSError as e:
        sys.stdout.write("\n")
        _out(f"  {RED}Failed to restart CUPS: {e}{RESET}")
        return False
    time.sleep(2)
    return True


# ── Backend error detection ──────────────────────────────────────────


def _is_cups_printer_healthy(printer_name: str) -> bool:
    """Check live CUPS state via lpstat. Returns True if enabled with no issues."""
    lpstat_path = shutil.which("lpstat")
    if not lpstat_path:
        return False
    try:
        r = subprocess.run(
            [lpstat_path, "-p", printer_name],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        for line in r.stdout.splitlines():
            if (
                printer_name in line
                and "idle" in line.lower()
                and "enabled" in line.lower()
            ):
                return True
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError):
        pass
    return False


def _find_backend_error_in_log(
    lines: list[str],
) -> tuple[str, str, str]:
    """Scan CUPS log lines (reversed) for backend errors.

    Returns:
        (backend_error, error_timestamp, last_success_timestamp)
    """
    backend_error = ""
    error_timestamp = ""
    last_success_timestamp = ""

    for line in reversed(lines):
        if (
            "backend errors" in line or "stopped with status" in line
        ) and not backend_error:
            backend_error = line.strip()
            ts_match = re.search(r"\[([^\]]+)\]", line)
            if ts_match:
                error_timestamp = ts_match.group(1)
        if ("Completed" in line or "total" in line) and error_timestamp:
            ts_match = re.search(r"\[([^\]]+)\]", line)
            if ts_match:
                last_success_timestamp = ts_match.group(1)
                break

    return backend_error, error_timestamp, last_success_timestamp


def _check_cups_backend_errors(
    printer_name: str,
) -> tuple[bool, str]:
    """Check CUPS error log for backend errors. Returns (has_errors, last_error)."""
    if _is_cups_printer_healthy(printer_name):
        return False, ""

    log_path = Path("/var/log/cups/error_log")
    if not log_path.exists():
        return False, ""
    try:
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return False, ""

    backend_error, error_timestamp, last_success_timestamp = _find_backend_error_in_log(
        lines
    )

    if not backend_error:
        return False, ""

    if last_success_timestamp and last_success_timestamp > error_timestamp:
        return False, ""

    return True, backend_error


# ── Queue status display ────────────────────────────────────────────


def display_cups_queue_status(queue: CUPSQueueStatus) -> None:
    """Display CUPS queue status and offer interactive fixes."""
    if not queue.printer_name:
        return
    if queue.enabled and not queue.jobs and not queue.has_backend_errors:
        return

    _out()
    _out(f"{BOLD}── Print Queue ──{RESET}")
    _out()

    if queue.has_backend_errors and queue.enabled and not queue.jobs:
        _out(f"  {YELLOW}{BOLD}⚡ CUPS backend has stale errors{RESET}")
        _out(
            f"  {DIM}New print jobs may silently fail."
            f" A CUPS restart usually fixes this.{RESET}"
        )
        _out()

    if not queue.enabled:
        _out(f"  {RED}{BOLD}⚠  Printer queue is DISABLED{RESET}")
        if queue.reason:
            _out(f"  {DIM}Reason: {queue.reason}{RESET}")
        _out()

    if queue.jobs:
        _out(f"  {BOLD}Pending jobs ({len(queue.jobs)}):{RESET}")
        for job in queue.jobs:
            _out(f"    {job.job_id}  {DIM}{job.user}  {job.size}B  {job.date}{RESET}")
        _out()

    _offer_queue_fix(queue)


# ── Interactive queue fix ────────────────────────────────────────────


def _offer_queue_fix(queue: CUPSQueueStatus) -> None:
    """Prompt the user to fix a disabled queue / pending jobs."""
    _out(f"  {BOLD}Available actions:{RESET}")

    options: list[str] = []
    if not queue.enabled and queue.jobs:
        _out(f"    {CYAN}1){RESET} Re-enable printer and retry all jobs")
        _out(f"    {CYAN}2){RESET} Re-enable printer and cancel all jobs")
        _out(f"    {CYAN}3){RESET} Cancel all jobs (keep printer disabled)")
        _out(f"    {CYAN}4){RESET} Restart CUPS service (fixes stale backend)")
        _out(f"    {CYAN}5){RESET} Restart CUPS + re-enable + retry all jobs")
        _out(f"    {CYAN}6){RESET} Do nothing")
        options = ["1", "2", "3", "4", "5", "6"]
    elif not queue.enabled:
        _out(f"    {CYAN}1){RESET} Re-enable printer")
        _out(f"    {CYAN}2){RESET} Restart CUPS service (fixes stale backend)")
        _out(f"    {CYAN}3){RESET} Do nothing")
        options = ["1", "2", "3"]
    elif queue.jobs:
        _out(f"    {CYAN}1){RESET} Cancel all pending jobs")
        _out(f"    {CYAN}2){RESET} Restart CUPS service (fixes stale backend)")
        _out(f"    {CYAN}3){RESET} Do nothing")
        options = ["1", "2", "3"]
    else:
        _out(f"    {CYAN}1){RESET} Restart CUPS service (fixes stale backend)")
        _out(f"    {CYAN}2){RESET} Do nothing")
        options = ["1", "2"]

    _out()
    choice = _prompt(f"  Choose [{'/'.join(options)}]: ")
    _out()

    if not queue.enabled and queue.jobs:
        _handle_disabled_with_jobs(queue, choice)
    elif not queue.enabled:
        _handle_disabled_no_jobs(queue, choice)
    elif queue.jobs:
        _handle_enabled_with_jobs(queue, choice)
    else:
        _handle_backend_errors_only(choice)


def _dwj_enable_only(printer_name: str) -> None:
    """Choice 1: re-enable printer so queued jobs are retried."""
    if _cups_enable_printer(printer_name):
        _out(f"  {GREEN}✓ Printer re-enabled. Jobs will be retried.{RESET}")


def _dwj_cancel_and_enable(printer_name: str) -> None:
    """Choice 2: cancel all jobs then re-enable."""
    _cups_cancel_all_jobs(printer_name)
    if _cups_enable_printer(printer_name):
        _out(f"  {GREEN}✓ All jobs cancelled and printer re-enabled.{RESET}")


def _dwj_cancel_only(printer_name: str) -> None:
    """Choice 3: cancel all jobs."""
    if _cups_cancel_all_jobs(printer_name):
        _out(f"  {GREEN}✓ All jobs cancelled.{RESET}")


def _dwj_restart_only(_printer_name: str) -> None:
    """Choice 4: restart CUPS."""
    if _cups_restart_service():
        _out(f"  {GREEN}✓ CUPS restarted.{RESET}")


def _dwj_restart_and_enable(printer_name: str) -> None:
    """Choice 5: restart CUPS and re-enable printer."""
    if _cups_restart_service():
        _cups_enable_printer(printer_name)
        _out(
            f"  {GREEN}✓ CUPS restarted, printer re-enabled."
            f" Jobs will be retried.{RESET}"
        )


_DWJ_ACTIONS: dict[str, Callable[[str], None]] = {
    "1": _dwj_enable_only,
    "2": _dwj_cancel_and_enable,
    "3": _dwj_cancel_only,
    "4": _dwj_restart_only,
    "5": _dwj_restart_and_enable,
}


def _handle_disabled_with_jobs(queue: CUPSQueueStatus, choice: str) -> None:
    """Handle fix for disabled printer with pending jobs."""
    action = _DWJ_ACTIONS.get(choice)
    if action is not None:
        action(queue.printer_name)
    else:
        _out(f"  {DIM}No changes made.{RESET}")


def _handle_disabled_no_jobs(queue: CUPSQueueStatus, choice: str) -> None:
    """Handle fix for disabled printer with no pending jobs."""
    if choice == "1":
        if _cups_enable_printer(queue.printer_name):
            _out(f"  {GREEN}✓ Printer re-enabled.{RESET}")
    elif choice == "2":
        if _cups_restart_service():
            _cups_enable_printer(queue.printer_name)
            _out(f"  {GREEN}✓ CUPS restarted and printer re-enabled.{RESET}")
    else:
        _out(f"  {DIM}No changes made.{RESET}")


def _handle_enabled_with_jobs(queue: CUPSQueueStatus, choice: str) -> None:
    """Handle fix for enabled printer with stuck jobs."""
    if choice == "1":
        if _cups_cancel_all_jobs(queue.printer_name):
            _out(f"  {GREEN}✓ All jobs cancelled.{RESET}")
    elif choice == "2":
        if _cups_restart_service():
            _out(f"  {GREEN}✓ CUPS restarted.{RESET}")
    else:
        _out(f"  {DIM}No changes made.{RESET}")


def _handle_backend_errors_only(choice: str) -> None:
    """Handle fix when only stale backend errors are detected."""
    if choice == "1":
        if _cups_restart_service():
            _out(f"  {GREEN}✓ CUPS restarted. Stale backend errors cleared.{RESET}")
    else:
        _out(f"  {DIM}No changes made.{RESET}")
