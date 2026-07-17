"""Consumable life tracking: page counters, replacement baselines, dropped pages.

Everything here hangs off one hard-won fact: CUPS cannot be trusted to say what
the printer actually did. Its page log only sees jobs it printed itself, and it
counts pages the printer silently discarded - it logged "total 50" for a job
that produced 3 sheets. Only the printer's own @PJL INFO PAGECOUNT is
authoritative, so replacement baselines are kept on that scale and the gap
between the two counters is what exposes dropped pages.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
import re

from python_pkg.brother_printer.constants import (
    CONSUMABLE_STATE_DIR,
    CUPS_PAGE_LOG_PATH,
    DRUM_RATED_PAGES,
    GREEN,
    PAGE_DROP_WARN_THRESHOLD,
    RESET,
    TONER_RATED_PAGES,
    _out,
)
from python_pkg.brother_printer.data_classes import (
    PageCountEstimate,
    PageDeliveryCheck,
)

logger = logging.getLogger(__name__)

CUPS_PAGE_LOG = Path(CUPS_PAGE_LOG_PATH)
CONSUMABLE_STATE_FILE = Path.home() / CONSUMABLE_STATE_DIR / "state.json"

# state.json schema versions. Version 1 (implicit, no "schema" key) recorded
# replacement baselines as CUPS page-log counts; version 2 records them on the
# printer's own lifetime counter. See _migrate_state_to_printer_scale.
STATE_SCHEMA_CUPS_SCALE = 1
STATE_SCHEMA_PRINTER_SCALE = 2


# ── Consumable state management ──────────────────────────────────────


def _get_cups_total_pages() -> int:
    """Parse CUPS page_log to get total pages printed (deduplicated by job)."""
    if not CUPS_PAGE_LOG.exists():
        return 0
    try:
        text = CUPS_PAGE_LOG.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 0
    jobs: dict[str, int] = {}
    for line in text.splitlines():
        match = re.search(r"\s(\d+)\s+\[.*?\]\s+total\s+(\d+)", line)
        if match:
            job_id = match.group(1)
            pages = int(match.group(2))
            jobs[job_id] = max(jobs.get(job_id, 0), pages)
    return sum(jobs.values())


def _load_consumable_state() -> dict[str, int]:
    """Load consumable replacement state from disk."""
    defaults: dict[str, int] = {
        "toner_replaced_at": 0,
        "drum_replaced_at": 0,
        "schema": STATE_SCHEMA_CUPS_SCALE,
        # Snapshot of both counters at the last successful printer read, used to
        # spot dropped pages and to place a CUPS-log figure on the printer's
        # scale when the printer cannot be reached.
        "last_printer_count": 0,
        "last_cups_total": 0,
    }
    if not CONSUMABLE_STATE_FILE.exists():
        return defaults
    try:
        data = json.loads(
            CONSUMABLE_STATE_FILE.read_text(encoding="utf-8"),
        )
        return {
            "toner_replaced_at": int(data.get("toner_replaced_at", 0)),
            "drum_replaced_at": int(data.get("drum_replaced_at", 0)),
            "schema": int(data.get("schema", STATE_SCHEMA_CUPS_SCALE)),
            "last_printer_count": int(data.get("last_printer_count", 0)),
            "last_cups_total": int(data.get("last_cups_total", 0)),
        }
    except (OSError, json.JSONDecodeError, ValueError, TypeError):
        return defaults


def _migrate_state_to_printer_scale(
    state: dict[str, int],
    printer_total: int,
) -> dict[str, int]:
    """Rebase replacement baselines from the CUPS page log onto the printer's counter.

    Baselines written before this migration counted pages the CUPS log had seen,
    which undercounts the printer's own lifetime counter by however many pages
    were printed without CUPS logging them.  Shift each baseline by the gap
    measured now, so "pages since replacement" - and therefore the reported
    percentages - stay put across the switch.

    A zero baseline means "never replaced" rather than "replaced at page zero",
    so it is left alone: on the printer's scale it already means "as old as the
    printer", which is the truthful reading.

    Args:
        state: Loaded state, possibly still on the CUPS page-log scale.
        printer_total: Lifetime page count from the printer's own counter.

    Returns:
        State on the printer's scale, migrated at most once.
    """
    if state.get("schema", STATE_SCHEMA_CUPS_SCALE) >= STATE_SCHEMA_PRINTER_SCALE:
        return state
    offset = printer_total - _get_cups_total_pages()
    migrated = dict(state)
    migrated["schema"] = STATE_SCHEMA_PRINTER_SCALE
    if offset > 0:
        for key in ("toner_replaced_at", "drum_replaced_at"):
            if state[key] > 0:
                migrated[key] = state[key] + offset
    _save_consumable_state(migrated)
    return migrated


def _save_consumable_state(state: dict[str, int]) -> None:
    """Persist consumable replacement state to disk."""
    CONSUMABLE_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONSUMABLE_STATE_FILE.write_text(
        json.dumps(state, indent=2) + "\n",
        encoding="utf-8",
    )


def reset_consumable(name: str, printer_total: int = 0) -> None:
    """Record current page count as replacement point for a consumable.

    Args:
        name: Consumable to reset, "toner" or "drum".
        printer_total: Lifetime count from the printer's own counter. Falls back
            to the CUPS page log when zero, i.e. the printer was unreachable.
    """
    total = printer_total if printer_total > 0 else _get_cups_total_pages()
    state = _load_consumable_state()
    key = f"{name}_replaced_at"
    state[key] = total
    # Baselines written here are already on the printer's scale, so mark the
    # state migrated to stop the rebase shifting them a second time.
    if printer_total > 0:
        state["schema"] = STATE_SCHEMA_PRINTER_SCALE
    _save_consumable_state(state)
    _out(f"{GREEN}✓ {name.capitalize()} counter reset at page count {total}.{RESET}")
    _out(f"  State saved to {CONSUMABLE_STATE_FILE}")


def _cups_total_on_printer_scale(state: dict[str, int]) -> int:
    """Express the CUPS page-log count on the printer's counter scale.

    Replacement baselines are stored against the printer's lifetime counter, so
    comparing a raw CUPS figure against them subtracts two different scales. The
    CUPS log runs behind the printer (it only sees jobs it printed itself), so
    the raw number reads too low - low enough to go negative and clamp to zero,
    which reported a spent cartridge as 100% full.

    Shift by the gap measured at the last successful printer read. It is an
    approximation, which is why callers flag the estimate as approximate.

    Args:
        state: Loaded consumable state holding the last counter snapshot.

    Returns:
        The CUPS total shifted onto the printer's scale, or the raw total when
        no snapshot exists to shift it by.
    """
    cups_total = _get_cups_total_pages()
    if cups_total <= 0:
        return 0
    offset = state["last_printer_count"] - state["last_cups_total"]
    if state["last_printer_count"] <= 0 or offset <= 0:
        return cups_total
    return cups_total + offset


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


def estimate_consumable_life(printer_total: int = 0) -> PageCountEstimate:
    """Estimate toner/drum life from pages printed since the last replacement.

    Args:
        printer_total: Lifetime count from @PJL INFO PAGECOUNT. When zero the
            printer could not be asked, so the CUPS page log stands in and the
            estimate is flagged approximate.

    Returns:
        The estimate; total_pages is zero when no counter could be read at all.
    """
    approximate = printer_total <= 0
    state = _load_consumable_state()
    total = _cups_total_on_printer_scale(state) if approximate else printer_total
    if total <= 0:
        return PageCountEstimate()
    if not approximate:
        state = _migrate_state_to_printer_scale(state, total)
    toner_pages = max(0, total - state["toner_replaced_at"])
    drum_pages = max(0, total - state["drum_replaced_at"])
    toner_pct = max(0, 100 - (toner_pages * 100 // TONER_RATED_PAGES))
    drum_pct = max(0, 100 - (drum_pages * 100 // DRUM_RATED_PAGES))
    return PageCountEstimate(
        total_pages=total,
        toner_pages=toner_pages,
        drum_pages=drum_pages,
        toner_pct_remaining=toner_pct,
        drum_pct_remaining=drum_pct,
        approximate=approximate,
        toner_exhausted=toner_pages >= TONER_RATED_PAGES,
        toner_low=toner_pages >= TONER_RATED_PAGES * 80 // 100,
        drum_near_end=drum_pages >= DRUM_RATED_PAGES * 90 // 100,
    )
