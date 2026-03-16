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
    """Estimated consumable life based on CUPS page count."""

    total_pages: int = 0
    toner_pages: int = 0
    drum_pages: int = 0
    toner_pct_remaining: int = 100
    drum_pct_remaining: int = 100
    toner_exhausted: bool = False
    toner_low: bool = False
    drum_near_end: bool = False


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
    port_status: USBPortStatus | None = None


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
    supply_descriptions: list[str] = field(default_factory=list)
    supply_max: list[str] = field(default_factory=list)
    supply_levels: list[str] = field(default_factory=list)
    error: str = ""


@dataclass
class SupplyStatus:
    """Processed supply level info for display."""

    color: str
    bar: str
    status_text: str
    warning: str
    needs_replacement: bool
