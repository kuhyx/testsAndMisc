"""Constants, status codes, and lookup tables for Brother printer checking."""

from __future__ import annotations

import sys

# ── Colors ───────────────────────────────────────────────────────────

RED = "\033[0;31m"
YELLOW = "\033[1;33m"
GREEN = "\033[0;32m"
CYAN = "\033[0;36m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

# ── SNMP supply level sentinel values ────────────────────────────────────────

SNMP_LEVEL_OK = -3
SNMP_LEVEL_LOW = -2
SUPPLY_LOW_PCT = 10
SUPPLY_WARN_PCT = 25
PROGRESS_BAR_WIDTH = 25

# Brother HL-1110 consumable page ratings
TONER_RATED_PAGES = 1000
DRUM_RATED_PAGES = 10000
CUPS_PAGE_LOG_PATH = "/var/log/cups/page_log"
CONSUMABLE_STATE_DIR = ".config/brother_printer"
MIN_LPSTAT_JOB_PARTS = 4

# How many pages CUPS may claim over the printer's own counter before we call
# it dropping pages. A small gap is just timing (a job finishing as we look);
# a large one means the printer is discarding work and saying nothing.
PAGE_DROP_WARN_THRESHOLD = 5

BROTHER_USB_VENDOR_ID = 0x04F9


def _out(text: str = "") -> None:
    """Write a line to stdout."""
    sys.stdout.write(text + "\n")


def _prompt(text: str) -> str:
    """Read user input with a prompt."""
    sys.stdout.write(text)
    sys.stdout.flush()
    return sys.stdin.readline().strip()


# ── PJL status codes ─────────────────────────────────────────────────
# Transcribed from the HP PJL Technical Reference Manual, Appendix D
# ("PJL Status Codes").  Brother publishes no PJL status table of its own,
# but an HL-1110 was probed on real hardware (2026-07-17) and matched the HP
# codes for every state that could be induced:
#
#     10001 READY   10003 WARMING UP   10023 PRINTING
#     40000 SLEEP   40021 TOP COVER OPEN   41213 NO PAPER
#
# Only codes documented in that reference appear below.  Anything else is
# reported as unknown by get_status_info() rather than guessed at: a previous
# revision of this table invented meanings (40000 "Paper Jam", 30010 "Toner
# Low", 41000 "Cover Open" ...) and consequently reported a sleeping printer
# as a critical paper jam, while a genuine toner-low warning (10006) was
# rendered as a benign "Processing".
#
# Format: code -> (severity, short_text, action)
# Severities: ok, info, warn, critical

_ORDER_TONER = "Order replacement toner cartridge (TN-1050/TN-1030 compatible)."

BROTHER_STATUS_CODES: dict[int, tuple[str, str, str]] = {
    # Informational (10xxx)
    10001: ("ok", "Ready", ""),
    10002: ("info", "Ready (offline)", "Press the power button to bring it online."),
    10003: ("ok", "Warming up", ""),
    10004: ("info", "Self test", ""),
    10005: ("info", "Resetting / clearing memory", ""),
    10006: ("warn", "Toner Low", _ORDER_TONER),
    10007: ("info", "Canceling job", ""),
    10014: ("info", "Printing", ""),
    10023: ("info", "Printing / processing job", ""),
    # Auto-continuable conditions (30xxx)
    30010: ("info", "Status buffer overflow", ""),
    # Potential operator intervention (35xxx)
    35078: ("ok", "Power save", ""),
    # Operator intervention required (40xxx).  40000 is flagged in the
    # reference as "not an error - the printer is waiting for data".
    40000: ("ok", "Sleep (standby)", ""),
    40010: (
        "critical",
        "No Toner Cartridge",
        "Install a toner cartridge (TN-1050/TN-1030 compatible).",
    ),
    40019: (
        "warn",
        "Remove Paper From Output Bin",
        "Take the printed pages out of the output bin.",
    ),
    40021: (
        "critical",
        "Cover Open",
        "Close the printer cover and check the toner cartridge is seated.",
    ),
    40022: ("critical", "Paper Jam", "Clear the paper jam and close all covers."),
    40026: ("critical", "Install Paper Tray", "Insert the paper tray."),
    40038: ("warn", "Toner Low", _ORDER_TONER),
    40050: (
        "critical",
        "Fuser Error (50 SERVICE)",
        "Power-cycle the printer. If the error persists, contact service.",
    ),
    40079: (
        "warn",
        "Offline",
        "The printer is offline. Press the power button to bring it online.",
    ),
}

# Code families that encode a sub-status in their trailing digits.  The
# HL-1110 reports 41213 for an empty tray, which places it in the reference's
# "Foreground Paper Loading (41xyy)" family - but its x/yy digits do not
# decode per the HP tray/media tables (x=2 "upper cassette", yy=13 "Japan B5"
# on a single-tray A4 printer).  So match the family and ignore the digits.
# Each entry is an inclusive low/high bound plus the usual status triple.

_STATUS_CODE_RANGES: tuple[tuple[int, int, tuple[str, str, str]], ...] = (
    (
        41000,
        41999,
        ("critical", "Out of Paper", "Load paper into the paper tray."),
    ),
    (
        50000,
        50999,
        (
            "critical",
            "Hardware Error",
            "Power-cycle the printer. If the error persists, contact service.",
        ),
    ),
)

# ── CUPS status code mappings ────────────────────────────────────────

# These translate what CUPS reports into the PJL codes above, for the
# fallback path used when the usblp device is unavailable and the printer
# cannot be asked directly.  Every value must name a real code from
# BROTHER_STATUS_CODES (or a range family), otherwise the fallback silently
# degrades to "unknown status".

_CUPS_REASONS_TO_STATUS: dict[str, int] = {
    "paused": 10002,
    "moving-to-paused": 10002,
    "toner-low": 40038,
    "toner-empty": 40010,
    "marker-supply-low": 40038,
    "marker-supply-empty": 40010,
    "media-empty": 41000,
    "media-needed": 41000,
    "media-jam": 40022,
    "cover-open": 40021,
    "door-open": 40021,
    "input-tray-missing": 40026,
}

_CUPS_STATE_TO_STATUS: dict[str, int] = {
    "idle": 10001,
    "processing": 10023,
    "stopped": 40079,
}

_ERROR_REASON_MAP: tuple[tuple[tuple[str, ...], str, str], ...] = (
    (("media-jam",), "40022", "Paper Jam"),
    (("cover-open", "door-open"), "40021", "Cover Open"),
    (("toner-empty",), "40010", "No Toner Cartridge"),
    (("toner-low",), "40038", "Toner Low"),
)


# States this tool infers itself, rather than reads off the printer: from the
# CUPS page-count estimate, or from an error bit whose cause we cannot name.
# They deliberately are not PJL numbers - borrowing a PJL code for a state the
# printer never reported is how the old table came to claim a sleeping printer
# had jammed.

DERIVED_TONER_END = "estimate:toner-end"
DERIVED_TONER_LOW = "estimate:toner-low"
DERIVED_CUPS_ERROR = "cups:error"

_DERIVED_STATUS_CODES: dict[str, tuple[str, str, str]] = {
    DERIVED_TONER_END: (
        "critical",
        "Toner End (estimated from page count)",
        _ORDER_TONER,
    ),
    DERIVED_TONER_LOW: ("warn", "Toner Low (estimated from page count)", _ORDER_TONER),
    DERIVED_CUPS_ERROR: (
        "warn",
        "Printer reports an error",
        "Check the printer display for details.",
    ),
}


def get_status_info(code: str) -> tuple[str, str, str]:
    """Look up a PJL status code. Returns (severity, text, action)."""
    derived = _DERIVED_STATUS_CODES.get(code)
    if derived is not None:
        return derived
    try:
        numeric = int(code)
    except (TypeError, ValueError):
        return _unknown_status(code)
    exact = BROTHER_STATUS_CODES.get(numeric)
    if exact is not None:
        return exact
    for low, high, info in _STATUS_CODE_RANGES:
        if low <= numeric <= high:
            return info
    return _unknown_status(code)


def _unknown_status(code: str) -> tuple[str, str, str]:
    """Describe a code that is not in the PJL reference. Never guesses."""
    return (
        "info",
        f"Unknown status (code {code})",
        "Check printer display for details.",
    )
