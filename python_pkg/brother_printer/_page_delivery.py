"""Dropped-page detection: CUPS's page log versus the printer's own counter.

Split out of :mod:`python_pkg.brother_printer.consumables` to keep it under
the 250-line cap. The state-file I/O stays in ``consumables`` because
``tests/test_consumables.py`` patches it there; it is imported here so
``tests/test_consumables_part2.py`` can patch it on this module for the two
functions that moved.
"""

from __future__ import annotations

from python_pkg.brother_printer.constants import PAGE_DROP_WARN_THRESHOLD
from python_pkg.brother_printer.consumables import (
    _get_cups_total_pages,
    _load_consumable_state,
    _save_consumable_state,
)
from python_pkg.brother_printer.data_classes import PageDeliveryCheck


def check_page_delivery(printer_total: int, *, queue_idle: bool) -> PageDeliveryCheck:
    """Compare pages CUPS logged against pages the printer actually counted.

    Only meaningful between jobs: mid-job, CUPS has logged pages the printer has
    not yet pulled off the wire, which would look identical to dropping them.
    Records a fresh snapshot of both counters whenever it runs cleanly.

    Args:
        printer_total: Lifetime count from the printer's own counter.
        queue_idle: False when a job is queued or printing, which makes any
            comparison meaningless.

    Returns:
        The comparison. suspected is True only when CUPS claims materially more
        pages than the printer recorded.
    """
    check = PageDeliveryCheck()
    if printer_total <= 0 or not queue_idle:
        return check
    state = _load_consumable_state()
    cups_total = _get_cups_total_pages()
    last_printer = state["last_printer_count"]
    last_cups = state["last_cups_total"]

    _snapshot_counters(state, printer_total, cups_total)

    if last_printer <= 0 or last_cups <= 0:
        # No baseline yet: this run establishes one.
        return check
    printer_delta = printer_total - last_printer
    cups_delta = cups_total - last_cups
    if printer_delta < 0 or cups_delta < 0:
        # Counter reset or the page log rotated; nothing to conclude.
        return check
    check.cups_pages = cups_delta
    check.printer_pages = printer_delta
    check.dropped = cups_delta - printer_delta
    check.suspected = check.dropped >= PAGE_DROP_WARN_THRESHOLD
    return check


def _snapshot_counters(
    state: dict[str, int],
    printer_total: int,
    cups_total: int,
) -> None:
    """Persist where both counters stood, for the next run to compare against."""
    if (
        state["last_printer_count"] == printer_total
        and state["last_cups_total"] == cups_total
    ):
        return
    updated = dict(state)
    updated["last_printer_count"] = printer_total
    updated["last_cups_total"] = cups_total
    _save_consumable_state(updated)
