"""Tests for brother_printer.data_classes module."""

from __future__ import annotations

from python_pkg.brother_printer.data_classes import (
    CUPSJob,
    CUPSQueueStatus,
    NetworkResult,
    PageCountEstimate,
    SupplyStatus,
    USBPortStatus,
    USBResult,
)


class TestCUPSJob:
    def test_create(self) -> None:
        job = CUPSJob(job_id="job-1", user="alice", size="1024", date="2025-01-01")
        assert job.job_id == "job-1"
        assert job.user == "alice"
        assert job.size == "1024"
        assert job.date == "2025-01-01"


class TestCUPSQueueStatus:
    def test_defaults(self) -> None:
        s = CUPSQueueStatus()
        assert s.printer_name == ""
        assert s.enabled is True
        assert s.reason == ""
        assert s.jobs == []
        assert s.has_backend_errors is False
        assert s.last_backend_error == ""


class TestPageCountEstimate:
    def test_defaults(self) -> None:
        p = PageCountEstimate()
        assert p.total_pages == 0
        assert p.toner_pct_remaining == 100
        assert p.drum_pct_remaining == 100
        assert p.toner_exhausted is False
        assert p.toner_low is False
        assert p.drum_near_end is False


class TestUSBPortStatus:
    def test_defaults(self) -> None:
        ps = USBPortStatus()
        assert ps.paper_empty is False
        assert ps.online is True
        assert ps.error is False
        assert ps.raw_byte == 0


class TestUSBResult:
    def test_defaults(self) -> None:
        r = USBResult()
        assert r.connection == "usb"
        assert r.device == ""
        assert r.product == "Brother Laser Printer"
        assert r.serial == ""
        assert r.status_code == ""
        assert r.display == ""
        assert r.online == ""
        assert r.economode == ""
        assert r.error == ""
        assert r.port_status is None


class TestNetworkResult:
    def test_defaults(self) -> None:
        r = NetworkResult()
        assert r.connection == "network"
        assert r.ip == ""
        assert r.product == "Unknown"
        assert r.supply_descriptions == []
        assert r.supply_max == []
        assert r.supply_levels == []
        assert r.error == ""


class TestSupplyStatus:
    def test_create(self) -> None:
        s = SupplyStatus(
            color="red",
            bar="[###]",
            status_text="50%",
            warning="low",
            needs_replacement=True,
        )
        assert s.color == "red"
        assert s.needs_replacement is True
