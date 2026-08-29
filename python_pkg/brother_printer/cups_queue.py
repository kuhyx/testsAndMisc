"""CUPS queue inspection, display, and interactive fix functions."""

from __future__ import annotations

from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

from python_pkg.brother_printer._cups_fallback import find_cups_printer_name
from python_pkg.brother_printer._query import run_command_text
from python_pkg.brother_printer.constants import (
    DIM,
    MIN_LPSTAT_JOB_PARTS,
    RED,
    RESET,
    _out,
)
from python_pkg.brother_printer.data_classes import CUPSJob, CUPSQueueStatus

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

    status_lines = run_command_text([lpstat_path, "-p", printer_name]).splitlines()
    for line in status_lines:
        if "printer" in line.lower() and printer_name in line:
            result.enabled, result.reason = _parse_lpstat_printer_line(line)
            break

    jobs_output = run_command_text([lpstat_path, "-o", printer_name])
    result.jobs = _parse_lpstat_jobs(jobs_output, printer_name)

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
    except subprocess.TimeoutExpired, subprocess.CalledProcessError, OSError:
        return False
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
                _out(f"  {RED}CUPS restart timed out (stuck backend process?).{RESET}")
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
            _out(f"  {RED}CUPS restart failed (exit code {proc.returncode}).{RESET}")
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
    for line in run_command_text([lpstat_path, "-p", printer_name]).splitlines():
        if (
            printer_name in line
            and "idle" in line.lower()
            and "enabled" in line.lower()
        ):
            return True
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
