"""SNMP network query functions for Brother printers."""

from __future__ import annotations

import shutil
import subprocess

from python_pkg.brother_printer.data_classes import NetworkResult


def _snmpwalk_cmd(
    path: str, community: str, timeout: int, ip: str, oid: str
) -> list[str]:
    """Build the snmpwalk command arguments."""
    return [path, "-v", "2c", "-c", community, "-t", str(timeout), "-OQvs", ip, oid]


def snmp_walk(ip: str, oid: str, community: str, timeout: int) -> list[str]:
    """Run snmpwalk and return cleaned values."""
    snmpwalk_path = shutil.which("snmpwalk")
    if not snmpwalk_path:
        return []
    try:
        r = subprocess.run(
            _snmpwalk_cmd(snmpwalk_path, community, timeout, ip, oid),
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        return [
            line.strip().strip('"')
            for line in r.stdout.strip().splitlines()
            if line.strip()
        ]
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError):
        return []


def _snmpget_cmd(
    path: str, community: str, timeout: int, ip: str, oid: str
) -> list[str]:
    """Build the snmpget command arguments."""
    return [path, "-v", "2c", "-c", community, "-t", str(timeout), ip, oid]


def _check_snmp_connectivity(ip: str, community: str, timeout: int) -> str | None:
    """Verify SNMP connectivity. Returns error message or None on success."""
    snmpget_path = shutil.which("snmpget")
    if not snmpget_path:
        return "snmpget not found. Install: sudo pacman -S net-snmp"
    try:
        subprocess.run(
            _snmpget_cmd(
                snmpget_path,
                community,
                timeout,
                ip,
                "1.3.6.1.2.1.43.11.1.1.6.1.1",
            ),
            capture_output=True,
            timeout=10,
            check=True,
        )
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, OSError):
        return f"Cannot reach printer at {ip} via SNMP."
    return None


def _build_network_result(ip: str, community: str, timeout: int) -> NetworkResult:
    """Collect all SNMP data into a NetworkResult."""

    def walk(oid: str) -> list[str]:
        return snmp_walk(ip, oid, community, timeout)

    return NetworkResult(
        ip=ip,
        product=" ".join(walk("1.3.6.1.2.1.25.3.2.1.3")[:1]) or "Unknown",
        serial=" ".join(walk("1.3.6.1.2.1.43.5.1.1.17")[:1]) or "",
        printer_status=" ".join(walk("1.3.6.1.2.1.25.3.5.1.1")[:1]) or "",
        device_status=" ".join(walk("1.3.6.1.2.1.25.3.2.1.5")[:1]) or "",
        display=" ".join(walk("1.3.6.1.2.1.43.16.5.1.2")[:3]) or "",
        page_count=" ".join(walk("1.3.6.1.2.1.43.10.2.1.4")[:1]) or "",
        supply_descriptions=walk("1.3.6.1.2.1.43.11.1.1.6"),
        supply_max=walk("1.3.6.1.2.1.43.11.1.1.8"),
        supply_levels=walk("1.3.6.1.2.1.43.11.1.1.9"),
    )


def query_network_snmp(ip: str) -> NetworkResult:
    """Query a Brother printer via SNMP over the network."""
    community = "public"
    timeout = 5
    error = _check_snmp_connectivity(ip, community, timeout)
    if error:
        return NetworkResult(ip=ip, error=error)
    return _build_network_result(ip, community, timeout)
