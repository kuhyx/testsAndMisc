"""Display and formatting functions for Brother printer status reports."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from python_pkg.brother_printer._page_count import (
    _display_consumables_reference,
    _display_page_count_estimate,
    _display_page_delivery_warning,
)
from python_pkg.brother_printer._queue_fix import display_cups_queue_status
from python_pkg.brother_printer._severity import (
    _SEVERITY_COLORS,
    _SEVERITY_ICONS,
    _SEVERITY_SUMMARIES,
)
from python_pkg.brother_printer._supply import _collect_supply_items
from python_pkg.brother_printer.constants import (
    BOLD,
    CYAN,
    DIM,
    GREEN,
    RED,
    RESET,
    YELLOW,
    _out,
    get_status_info,
)
from python_pkg.brother_printer.cups_queue import get_cups_queue_status

if TYPE_CHECKING:
    from python_pkg.brother_printer.data_classes import (
        NetworkResult,
        USBResult,
    )

__all__ = ["display_network_results", "display_usb_results"]


def _display_report_header() -> None:
    """Print the report banner box."""
    _out()
    _out(f"{BOLD}╔══════════════════════════════════════════════════╗{RESET}")
    _out(f"{BOLD}║      Brother Laser Printer Status Report         ║{RESET}")
    _out(f"{BOLD}╚══════════════════════════════════════════════════╝{RESET}")
    _out()


# ── USB display helpers ──────────────────────────────────────────────


def _display_usb_device_info(result: USBResult) -> None:
    """Print device info block for USB results."""
    _out(f"{BOLD}Printer:{RESET}    {result.product or 'Unknown'}")
    _out(f"{BOLD}Connection:{RESET} USB")
    if result.serial:
        _out(f"{BOLD}Serial:{RESET}     {result.serial}")

    if result.online == "TRUE":
        _out(f"{BOLD}Online:{RESET}     {GREEN}Yes{RESET}")
    elif result.online == "FALSE":
        _out(f"{BOLD}Online:{RESET}     {YELLOW}No (needs attention){RESET}")

    _out()

    if result.economode:
        if result.economode == "ON":
            _out(
                f"{BOLD}Toner Save:{RESET} {GREEN}ON{RESET}"
                " (extends toner life, lighter prints)"
            )
        else:
            _out(f"{BOLD}Toner Save:{RESET} OFF")


def _format_status_detail(
    severity: str, short_text: str, action: str, result: USBResult
) -> None:
    """Print severity icon, display text, and action."""
    color = _SEVERITY_COLORS.get(severity, GREEN)
    icon = _SEVERITY_ICONS.get(severity, "✓")

    _out(f"  {color}{BOLD}{icon}  {short_text}{RESET}")
    if result.display and result.display != short_text:
        _out(f"  {DIM}Display: {result.display}{RESET}")
    _out(f"  {DIM}Status code: {result.status_code}{RESET}")

    if action:
        _out()
        _out(f"  {color}{BOLD}Action:{RESET} {color}{action}{RESET}")
    _out()
    _out(_SEVERITY_SUMMARIES.get(severity, ""))


def _display_pjl_status(result: USBResult) -> None:
    """Display PJL status code interpretation."""
    _out()
    _out(f"{BOLD}── Printer Status ──{RESET}")
    _out()

    if not result.status_code:
        _out(f"  {YELLOW}Could not read status from printer.{RESET}")
        if result.display:
            _out(f"  Display message: {BOLD}{result.display}{RESET}")
        return

    severity, short_text, action = get_status_info(result.status_code)
    _format_status_detail(severity, short_text, action, result)


def _display_cups_fallback_note(result: USBResult) -> None:
    """Show a note when running in CUPS fallback mode."""
    _out()
    if result.port_status is not None:
        _out(
            f"  {DIM}Note: Hardware status obtained via USB port query."
            f" Toner/drum percentages not available.{RESET}"
        )
    else:
        _out(
            f"  {DIM}Note: pyusb not available; status obtained via"
            f" CUPS only. Detailed toner/drum levels are not"
            f" available in this mode.{RESET}"
        )


# ── USB results display ─────────────────────────────────────────────


def display_usb_results(result: USBResult) -> None:
    """Print a formatted report for USB PJL query results."""
    if result.error:
        _out(f"{RED}Error: {result.error}{RESET}")
        sys.exit(1)

    _display_report_header()
    _display_usb_device_info(result)
    _display_pjl_status(result)

    if result.device == "cups":
        _display_cups_fallback_note(result)

    _out()
    printer_total = int(result.page_count) if result.page_count.isdigit() else 0
    queue = get_cups_queue_status()
    _display_page_delivery_warning(printer_total, queue_idle=not queue.jobs)
    _display_page_count_estimate(printer_total)
    _display_consumables_reference()

    display_cups_queue_status(queue)


# ── Network supply level helpers ─────────────────────────────────────


def _display_supply_warnings(*, needs_replacement: bool, warnings: list[str]) -> None:
    """Display supply level warnings summary."""
    _out()
    if needs_replacement:
        _out(f"{RED}{BOLD}⚠  ACTION NEEDED:{RESET}")
        for w in warnings:
            _out(f"   {RED}• {w}{RESET}")
    elif warnings:
        _out(f"{YELLOW}{BOLD}⚡ HEADS UP:{RESET}")
        for w in warnings:
            _out(f"   {YELLOW}• {w}{RESET}")
    else:
        _out(f"{GREEN}{BOLD}✓  All consumables are at healthy levels.{RESET}")


def _display_supply_levels(result: NetworkResult) -> None:
    """Display consumable supply levels section."""
    _out()
    _out(f"{BOLD}── Consumable Levels ──{RESET}")
    _out()

    needs_replacement = False
    warnings: list[str] = []
    items, descs = _collect_supply_items(result)

    for desc, item in zip(descs, items, strict=True):
        _out(
            f"  {BOLD}{desc:<25}{RESET}"
            f" {item.color}{item.bar_text} {item.status_text}{RESET}"
        )
        if item.needs_replacement:
            needs_replacement = True
        if item.warning:
            warnings.append(item.warning)

    _display_supply_warnings(needs_replacement=needs_replacement, warnings=warnings)


def _display_network_device_info(result: NetworkResult) -> None:
    """Display device info section for network results."""
    _out(f"{BOLD}Printer:{RESET}    {result.product or 'Unknown'}")
    _out(f"{BOLD}Connection:{RESET} Network ({result.ip})")
    if result.serial:
        _out(f"{BOLD}Serial:{RESET}     {result.serial}")
    if result.display:
        _out(f"{BOLD}Display:{RESET}    {result.display}")
    if result.page_count and result.page_count.isdigit():
        _out(f"{BOLD}Pages:{RESET}      {result.page_count} total")


# ── Network results display ──────────────────────────────────────────


def display_network_results(result: NetworkResult) -> None:
    """Print a formatted report for SNMP network query results."""
    if result.error:
        _out(f"{RED}Error: {result.error}{RESET}")
        sys.exit(1)

    _display_report_header()
    _display_network_device_info(result)
    _display_supply_levels(result)

    _out()
    _out(
        f"{CYAN}Tip: Visit http://{result.ip} for the full web management"
        f" interface.{RESET}"
    )
    _out()
