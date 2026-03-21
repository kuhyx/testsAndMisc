"""Display and formatting functions for Brother printer status reports."""

from __future__ import annotations

import sys

from python_pkg.brother_printer.constants import (
    BOLD,
    CYAN,
    DIM,
    DRUM_RATED_PAGES,
    GREEN,
    PROGRESS_BAR_WIDTH,
    RED,
    RESET,
    SNMP_LEVEL_LOW,
    SNMP_LEVEL_OK,
    SUPPLY_LOW_PCT,
    SUPPLY_WARN_PCT,
    TONER_RATED_PAGES,
    YELLOW,
    _out,
    get_status_info,
)
from python_pkg.brother_printer.cups_queue import (
    display_cups_queue_status,
    get_cups_queue_status,
)
from python_pkg.brother_printer.cups_service import estimate_consumable_life
from python_pkg.brother_printer.data_classes import (
    NetworkResult,
    SupplyStatus,
    USBResult,
)

# ── Shared display helpers ───────────────────────────────────────────


def _display_report_header() -> None:
    """Print the report banner box."""
    _out()
    _out(f"{BOLD}╔══════════════════════════════════════════════════╗{RESET}")
    _out(f"{BOLD}║      Brother Laser Printer Status Report         ║{RESET}")
    _out(f"{BOLD}╚══════════════════════════════════════════════════╝{RESET}")
    _out()


def _display_page_count_estimate() -> None:
    """Show estimated consumable life based on CUPS page count."""
    estimate = estimate_consumable_life()
    if estimate.total_pages <= 0:
        return
    _out(f"{BOLD}── Page Count Estimate ──{RESET}")
    _out()
    _out(
        f"  {BOLD}Total pages printed:{RESET} {estimate.total_pages}"
        f"  (toner: {estimate.toner_pages} since replacement,"
        f" drum: {estimate.drum_pages} since replacement)"
    )
    _out()
    # Toner bar
    toner_pct = estimate.toner_pct_remaining
    toner_filled = toner_pct * PROGRESS_BAR_WIDTH // 100
    toner_empty = PROGRESS_BAR_WIDTH - toner_filled
    toner_bar = f"[{'█' * toner_filled}{'░' * toner_empty}]"
    if estimate.toner_exhausted:
        toner_color = RED
        toner_note = " ← REPLACE NOW"
    elif estimate.toner_low:
        toner_color = YELLOW
        toner_note = " ← order soon"
    else:
        toner_color = GREEN
        toner_note = ""
    _out(
        f"  {BOLD}Toner:{RESET} {toner_color}{toner_bar} ~{toner_pct}%"
        f"{toner_note}{RESET}"
    )
    # Drum bar
    drum_pct = estimate.drum_pct_remaining
    drum_filled = drum_pct * PROGRESS_BAR_WIDTH // 100
    drum_empty = PROGRESS_BAR_WIDTH - drum_filled
    drum_bar = f"[{'█' * drum_filled}{'░' * drum_empty}]"
    if estimate.drum_near_end:
        drum_color = YELLOW
        drum_note = " ← nearing end"
    else:
        drum_color = GREEN
        drum_note = ""
    _out(f"  {BOLD}Drum:{RESET}  {drum_color}{drum_bar} ~{drum_pct}%{drum_note}{RESET}")
    _out(
        f"  {DIM}Based on pages since last replacement"
        f" vs rated capacity (toner ~{TONER_RATED_PAGES},"
        f" drum ~{DRUM_RATED_PAGES}).{RESET}"
    )
    _out(f"  {DIM}Reset after replacing: --reset-toner or --reset-drum{RESET}")
    if estimate.toner_exhausted:
        _out()
        _out(
            f"  {RED}{BOLD}⚠  Toner is likely exhausted."
            f" This is probably why the orange light is flashing.{RESET}"
        )
    _out()


def _display_consumables_reference() -> None:
    """Print compatible consumables reference."""
    _out(f"{BOLD}── Compatible Consumables ──{RESET}")
    _out()
    _out(f"  {BOLD}Toner:{RESET} TN-1050 / TN-1030 (or compatible third-party)")
    _out(f"  {BOLD}Drum:{RESET}  DR-1050 / DR-1030 (or compatible third-party)")
    _out(f"  {DIM}  Toner rated ~1000 pages; Drum rated ~10000 pages.{RESET}")
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
    _display_page_count_estimate()
    _display_consumables_reference()

    queue = get_cups_queue_status()
    display_cups_queue_status(queue)


# ── Network supply level helpers ─────────────────────────────────────


def _classify_percentage_level(desc: str, pct: int) -> tuple[int, str, str, str, bool]:
    """Classify a supply by its calculated percentage."""
    if pct <= SUPPLY_LOW_PCT:
        return pct, f"{pct}%", RED, f"{desc} at {pct}%.", True
    if pct <= SUPPLY_WARN_PCT:
        return pct, f"{pct}%", YELLOW, f"{desc} at {pct}% -- order soon.", False
    return pct, f"{pct}%", GREEN, "", False


def _classify_supply_level(
    desc: str, max_val: int, level: int
) -> tuple[int, str, str, str, bool]:
    """Classify a supply level. Returns (pct, status, color, warning, replace)."""
    if level == SNMP_LEVEL_OK:
        return -1, "OK", GREEN, "", False
    if level == SNMP_LEVEL_LOW:
        return -1, "LOW", RED, f"{desc} is LOW.", True
    if level == 0:
        return 0, "EMPTY", RED, f"{desc} is EMPTY -- replace now!", True
    if max_val > 0:
        pct = min(level * 100 // max_val, 100)
        return _classify_percentage_level(desc, pct)
    return -1, "", GREEN, "", False


def _format_supply_bar(pct: int) -> str:
    """Build a progress bar string for a supply percentage."""
    if pct < 0:
        return ""
    filled = pct * PROGRESS_BAR_WIDTH // 100
    empty = PROGRESS_BAR_WIDTH - filled
    return f"[{'█' * filled}{'░' * empty}]"


def _process_supply_item(desc: str, max_val: int, level: int) -> SupplyStatus:
    """Process a single supply item into display info."""
    pct, status_text, color, warning, needs_replacement = _classify_supply_level(
        desc, max_val, level
    )
    bar = _format_supply_bar(pct)
    return SupplyStatus(color, bar, status_text, warning, needs_replacement)


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


def _parse_supply_value(values: list[str], index: int) -> int:
    """Safely parse an integer from a supply value list."""
    try:
        return int(values[index])
    except (IndexError, ValueError):
        return 0


def _collect_supply_items(
    result: NetworkResult,
) -> tuple[list[SupplyStatus], list[str]]:
    """Parse and collect supply items with their descriptions."""
    items: list[SupplyStatus] = []
    descs: list[str] = []
    for i, desc in enumerate(result.supply_descriptions):
        max_val = _parse_supply_value(result.supply_max, i)
        level = _parse_supply_value(result.supply_levels, i)
        items.append(_process_supply_item(desc, max_val, level))
        descs.append(desc)
    return items, descs


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
            f" {item.color}{item.bar} {item.status_text}{RESET}"
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
