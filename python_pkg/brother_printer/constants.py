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

BROTHER_USB_VENDOR_ID = 0x04F9


def _out(text: str = "") -> None:
    """Write a line to stdout."""
    sys.stdout.write(text + "\n")


def _prompt(text: str) -> str:
    """Read user input with a prompt."""
    sys.stdout.write(text)
    sys.stdout.flush()
    return sys.stdin.readline().strip()


# ── Brother PJL status codes ────────────────────────────────────────
# Documented in Brother PJL Technical Reference.
# Format: code -> (severity, short_text, action)
# Severities: ok, info, warn, critical

BROTHER_STATUS_CODES: dict[int, tuple[str, str, str]] = {
    10001: ("ok", "Ready", ""),
    10002: ("ok", "Sleep", ""),
    10003: ("info", "Self-test / Calibrating", ""),
    10004: ("ok", "Warming up", ""),
    10005: ("ok", "Cooling down", ""),
    10006: ("info", "Processing", ""),
    10007: ("info", "Printing", ""),
    10014: ("ok", "Cancelling", ""),
    10023: ("info", "Waiting", ""),
    # Toner
    30010: (
        "warn",
        "Toner Low",
        "Order replacement toner cartridge (TN-1050/TN-1030 compatible).",
    ),
    30038: (
        "warn",
        "Toner Low",
        "Order replacement toner cartridge (TN-1050/TN-1030 compatible).",
    ),
    40038: (
        "warn",
        "Toner Low",
        "Order replacement toner cartridge (TN-1050/TN-1030 compatible).",
    ),
    40309: (
        "critical",
        "Replace Toner",
        "The toner cartridge needs immediate replacement (TN-1050/TN-1030 compatible).",
    ),
    40310: (
        "critical",
        "Toner End",
        "The toner cartridge is empty. Replace now (TN-1050/TN-1030 compatible).",
    ),
    # Drum
    30201: (
        "warn",
        "Drum End Soon",
        "The drum unit is nearing end of life. Order replacement (DR-1050 compatible).",
    ),
    40201: (
        "warn",
        "Drum End Soon",
        "The drum unit is nearing end of life. Order replacement (DR-1050 compatible).",
    ),
    40019: (
        "critical",
        "Replace Drum",
        "The drum unit must be replaced (DR-1050 compatible).",
    ),
    40020: (
        "critical",
        "Drum Stop",
        "The drum unit must be replaced immediately (DR-1050 compatible).",
    ),
    # Paper / feed
    40000: ("critical", "Paper Jam", "Clear the paper jam and close all covers."),
    40300: (
        "critical",
        "No Paper / Tray Open",
        "Load paper or close the paper tray.",
    ),
    40302: ("critical", "No Paper", "Load paper into the paper tray."),
    40016: ("warn", "Paper Feed Error", "Check paper tray and re-seat paper."),
    # Cover
    41000: ("critical", "Cover Open", "Close the top cover of the printer."),
    41001: ("critical", "Cover Open", "Close the front cover of the printer."),
    # Others
    35078: ("info", "Manual Feed", "Load paper in the manual feed slot."),
    42000: (
        "critical",
        "Machine Error",
        "Power-cycle the printer. If error persists, contact service.",
    ),
}

# ── CUPS status code mappings ────────────────────────────────────────

_CUPS_REASONS_TO_STATUS: dict[str, int] = {
    "paused": 10023,
    "moving-to-paused": 10023,
    "toner-low": 30010,
    "toner-empty": 40310,
    "marker-supply-low": 30010,
    "marker-supply-empty": 40310,
    "media-empty": 40302,
    "media-needed": 40302,
    "media-jam": 40000,
    "cover-open": 41000,
    "door-open": 41000,
    "input-tray-missing": 40300,
}

_CUPS_STATE_TO_STATUS: dict[str, int] = {
    "idle": 10001,
    "processing": 10007,
    "stopped": 10023,
}

_ERROR_REASON_MAP: tuple[tuple[tuple[str, ...], str, str], ...] = (
    (("media-jam",), "40000", "Paper Jam"),
    (("cover-open", "door-open"), "41000", "Cover Open"),
    (("toner-empty",), "40310", "Toner End"),
    (("toner-low",), "30010", "Toner Low"),
)


def get_status_info(code: str) -> tuple[str, str, str]:
    """Look up a PJL status code. Returns (severity, text, action)."""
    try:
        return BROTHER_STATUS_CODES[int(code)]
    except (KeyError, ValueError):
        return (
            "info",
            f"Unknown status (code {code})",
            "Check printer display for details.",
        )
