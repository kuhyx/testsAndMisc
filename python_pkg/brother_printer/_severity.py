"""The icon, colour and closing summary for each PJL severity.

Split out of :mod:`python_pkg.brother_printer.display` to keep it under the
250-line cap. Pure data: no test patches these tables, so unlike most of
``display`` they were free to move.
"""

from __future__ import annotations

from python_pkg.brother_printer.constants import (
    BOLD,
    CYAN,
    GREEN,
    RED,
    RESET,
    YELLOW,
)

_SEVERITY_ICONS: dict[str, str] = {
    "ok": "✓",
    "info": "i",
    "warn": "⚡",
    "critical": "⚠",
}
_SEVERITY_COLORS: dict[str, str] = {
    "ok": GREEN,
    "info": CYAN,
    "warn": YELLOW,
    "critical": RED,
}
_SEVERITY_SUMMARIES: dict[str, str] = {
    "ok": f"{GREEN}{BOLD}✓  Printer is healthy. No replacements needed.{RESET}",
    "info": (
        f"{CYAN}{BOLD}i  Printer is busy/processing. No replacements needed.{RESET}"
    ),
    "warn": (
        f"{YELLOW}{BOLD}⚡ WARNING: Maintenance will be needed"
        f" soon.{RESET}\n{YELLOW}   Order replacement parts"
        f" now to avoid interruption.{RESET}"
    ),
    "critical": (
        f"{RED}{BOLD}⚠  ACTION REQUIRED: Replacement or fix needed now!{RESET}"
    ),
}
