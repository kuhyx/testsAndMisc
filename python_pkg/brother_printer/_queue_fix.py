"""CUPS queue status display and the interactive queue-fix prompt.

Split out of :mod:`python_pkg.brother_printer.cups_queue` to keep it under the
250-line cap. The ``_cups_*`` action primitives deliberately stay in
``cups_queue``: ``tests/test_cups_queue.py`` patches ``subprocess`` and
``time`` on that module, and moving them would let a real ``subprocess.run``
reach the live CUPS daemon.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from python_pkg.brother_printer.constants import (
    BOLD,
    CYAN,
    DIM,
    GREEN,
    RED,
    RESET,
    YELLOW,
    _out,
    _prompt,
)
from python_pkg.brother_printer.cups_queue import (
    _cups_cancel_all_jobs,
    _cups_enable_printer,
    _cups_restart_service,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from python_pkg.brother_printer.data_classes import CUPSQueueStatus


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
