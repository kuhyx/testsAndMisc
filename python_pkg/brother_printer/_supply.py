"""Turning a raw SNMP supply reading into a percentage, a bar and a verdict.

Split out of :mod:`python_pkg.brother_printer.display` to keep it under the
250-line cap. Only the arithmetic lives here. The functions that *print*
(``_display_supply_levels``, ``_display_supply_warnings``) stay in ``display``
because ``tests/test_display_part2.py`` patches them there, and a patched name
has to remain resolvable in the module the test names.

``display`` re-exports everything below, because the tests import these names
from there rather than from here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from python_pkg.brother_printer.constants import (
    BOLD,
    GREEN,
    PROGRESS_BAR_WIDTH,
    RED,
    RESET,
    SNMP_LEVEL_LOW,
    SNMP_LEVEL_OK,
    SUPPLY_LOW_PCT,
    SUPPLY_WARN_PCT,
    YELLOW,
    _out,
)
from python_pkg.brother_printer.data_classes import SupplyStatus

if TYPE_CHECKING:
    from python_pkg.brother_printer.data_classes import NetworkResult


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
    bar_text = _format_supply_bar(pct)
    return SupplyStatus(color, bar_text, status_text, warning, needs_replacement)


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
    for i, desc in enumerate(result.supplies.descriptions):
        max_val = _parse_supply_value(result.supplies.max_values, i)
        level = _parse_supply_value(result.supplies.levels, i)
        items.append(_process_supply_item(desc, max_val, level))
        descs.append(desc)
    return items, descs


def render_life_bar(
    label: str,
    pct: int,
    *,
    exhausted: bool = False,
    low: bool = False,
    exhausted_note: str = "",
    low_note: str = "",
) -> None:
    """Print one consumable's remaining-life bar.

    The toner and drum bars in the page-count estimate were byte-for-byte the
    same logic with different colours and notes, which is what this collapses.

    Args:
        label: Displayed name, already padded by the caller if needed.
        pct: Percentage remaining, 0-100.
        exhausted: Render red with ``exhausted_note``.
        low: Render yellow with ``low_note``. Ignored when *exhausted*.
        exhausted_note: Suffix shown when *exhausted*.
        low_note: Suffix shown when *low*.
    """
    filled = pct * PROGRESS_BAR_WIDTH // 100
    meter = f"[{'█' * filled}{'░' * (PROGRESS_BAR_WIDTH - filled)}]"
    if exhausted:
        color, note = RED, exhausted_note
    elif low:
        color, note = YELLOW, low_note
    else:
        color, note = GREEN, ""
    _out(f"  {BOLD}{label}{RESET} {color}{meter} ~{pct}%{note}{RESET}")
