"""Data classes for Brother printer status information."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CUPSJob:
    """A single CUPS print job."""

    job_id: str
    user: str
    size: str
    date: str


@dataclass
class CUPSQueueStatus:
    """Status of the CUPS print queue for a printer."""

    printer_name: str = ""
    enabled: bool = True
    reason: str = ""
    jobs: list[CUPSJob] = field(default_factory=list)
    has_backend_errors: bool = False
    last_backend_error: str = ""


@dataclass
class PageCountEstimate:
    """Estimated consumable life based on the printer's lifetime page count."""

    total_pages: int = 0
    toner_pages: int = 0
    drum_pages: int = 0
    toner_pct_remaining: int = 100
    drum_pct_remaining: int = 100
    toner_exhausted: bool = False
    toner_low: bool = False
    drum_near_end: bool = False
    # True when total_pages came from the CUPS page log instead of the
    # printer's own counter.  The log only sees jobs CUPS itself printed, so
    # it undercounts and the percentages read optimistically high.
    approximate: bool = False


@dataclass
class PageDeliveryCheck:
    """Pages CUPS claims it sent versus pages the printer's counter recorded.

    CUPS reports a job as successful once the data leaves the machine, so a page
    the printer silently drops still shows up as "printed". The HL-1110 does
    exactly that when a page's 600 dpi raster overflows its ~1 MB of memory: it
    discards the page, stays READY, and reports no error anywhere. Comparing the
    two counters is the only way to notice.
    """

    cups_pages: int = 0
    printer_pages: int = 0
    dropped: int = 0
    suspected: bool = False


@dataclass
class USBPortStatus:
    """IEEE 1284 USB printer port status bits."""

    paper_empty: bool = False
    online: bool = True
    error: bool = False
    raw_byte: int = 0


@dataclass
class USBResult:
    """Result from a USB PJL query."""

    connection: str = "usb"
    device: str = ""
    product: str = "Brother Laser Printer"
    serial: str = ""
    status_code: str = ""
    display: str = ""
    online: str = ""
    economode: str = ""
    error: str = ""
    # Lifetime page count from @PJL INFO PAGECOUNT: the printer's own counter,
    # and the authoritative one.  Empty when the printer could not be asked
    # (CUPS fallback mode), which forces the estimate onto the CUPS page log.
    page_count: str = ""
    port_status: USBPortStatus | None = None


@dataclass
class SupplyReadings:
    """Parallel SNMP supply tables (descriptions, capacities, current levels).

    The three lists are always populated and indexed together, so they travel
    as one object rather than three loose fields on NetworkResult.
    """

    descriptions: list[str] = field(default_factory=list)
    max_values: list[str] = field(default_factory=list)
    levels: list[str] = field(default_factory=list)


@dataclass
class NetworkResult:
    """Result from an SNMP network query."""

    connection: str = "network"
    ip: str = ""
    product: str = "Unknown"
    serial: str = ""
    printer_status: str = ""
    device_status: str = ""
    display: str = ""
    page_count: str = ""
    supplies: SupplyReadings = field(default_factory=SupplyReadings)
    error: str = ""


@dataclass
class SupplyStatus:
    """Processed supply level info for display."""

    color: str
    bar_text: str
    status_text: str
    warning: str
    needs_replacement: bool
