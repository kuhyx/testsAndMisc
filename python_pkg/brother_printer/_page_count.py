"""Page-count estimates and the dropped-page warning.

Split out of :mod:`python_pkg.brother_printer.display` to keep it under the
250-line cap. ``estimate_consumable_life`` and ``check_page_delivery`` are
patched by ``tests/test_display_part3.py``, so they are imported here rather
than through ``display``.
"""

from __future__ import annotations

from python_pkg.brother_printer._supply import render_life_bar
from python_pkg.brother_printer.constants import (
    BOLD,
    DIM,
    DRUM_RATED_PAGES,
    RED,
    RESET,
    TONER_RATED_PAGES,
    YELLOW,
    _out,
)
from python_pkg.brother_printer.consumables import (
    check_page_delivery,
    estimate_consumable_life,
)


def _display_page_delivery_warning(printer_total: int, *, queue_idle: bool) -> None:
    """Warn when CUPS claims more pages than the printer actually counted.

    Args:
        printer_total: Lifetime count from the printer's own counter.
        queue_idle: False while a job is queued or printing, when the two
            counters legitimately disagree.
    """
    check = check_page_delivery(printer_total, queue_idle=queue_idle)
    if not check.suspected:
        return
    _out(f"{BOLD}── Dropped Pages ──{RESET}")
    _out()
    _out(
        f"  {RED}{BOLD}⚠  {check.dropped} pages did not print.{RESET}"
        f"  {RED}CUPS sent {check.cups_pages} pages since the last check;"
        f" the printer's own counter advanced by"
        f" {check.printer_pages}.{RESET}"
    )
    _out()
    _out(
        f"  {DIM}The printer discards pages whose 600 dpi raster does not fit"
        f" its memory, stays READY, and reports no error - and CUPS still calls"
        f" the job successful. Reprint at a lower resolution:{RESET}"
    )
    _out(f"  {DIM}  lp -o Resolution=300dpi <file>{RESET}")
    _out()


def _display_page_count_estimate(printer_total: int = 0) -> None:
    """Show estimated consumable life based on the printer's page count.

    Args:
        printer_total: Lifetime count from the printer's own counter, or zero
            when it could not be read and the CUPS page log has to stand in.
    """
    estimate = estimate_consumable_life(printer_total)
    if estimate.total_pages <= 0:
        return
    _out(f"{BOLD}── Page Count Estimate ──{RESET}")
    _out()
    _out(
        f"  {BOLD}Total pages printed:{RESET} {estimate.total_pages}"
        f"  (toner: {estimate.toner_pages} since replacement,"
        f" drum: {estimate.drum_pages} since replacement)"
    )
    if estimate.approximate:
        _out(
            f"  {YELLOW}Approximate: counted from the CUPS log, not the"
            f" printer's own counter, so it misses pages CUPS never saw"
            f" and reads high.{RESET}"
        )
    _out()
    render_life_bar(
        "Toner:",
        estimate.toner_pct_remaining,
        exhausted=estimate.toner_exhausted,
        low=estimate.toner_low,
        exhausted_note=" ← REPLACE NOW",
        low_note=" ← order soon",
    )
    render_life_bar(
        "Drum: ",
        estimate.drum_pct_remaining,
        low=estimate.drum_near_end,
        low_note=" ← nearing end",
    )
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
