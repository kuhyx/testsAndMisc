"""Shared subprocess and CUPS-query helpers for the brother_printer package.

Centralises the short, non-checking command invocation and the ``lpstat``-based
USB-info parsing that the CUPS, USB, and status modules all repeat, so the
subprocess boilerplate and URI parsing live in exactly one place.
"""

from __future__ import annotations

import logging
import subprocess
import urllib.parse

logger = logging.getLogger(__name__)


def run_command_text(args: list[str], *, timeout: float = 5) -> str:
    """Run ``args`` and return its captured stdout, or "" on any failure.

    A non-checking run with captured text output and a short timeout.  Any
    timeout, subprocess, or OS error is swallowed and reported as empty output,
    so callers can split/scan the result unconditionally.

    Args:
        args: The command and its arguments.
        timeout: Seconds before the command is killed.

    Returns:
        The command's standard output, or an empty string on any failure.
    """
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError):
        logger.debug("Command failed: %s", args, exc_info=True)
        return ""
    return result.stdout


def parse_cups_usb_uri(uri: str, info: dict[str, str]) -> None:
    """Extract the product and serial from a CUPS ``usb://`` URI into ``info``."""
    parsed = urllib.parse.urlparse(uri)
    info["product"] = urllib.parse.unquote(parsed.path.lstrip("/"))
    query = urllib.parse.parse_qs(parsed.query)
    if "serial" in query:
        info["serial"] = query["serial"][0]


def printer_info_from_cups() -> dict[str, str]:
    """Return the Brother printer's model/serial as parsed from ``lpstat -v``."""
    info: dict[str, str] = {"product": "", "serial": ""}
    for line in run_command_text(["/usr/bin/lpstat", "-v"]).splitlines():
        if "Brother" in line:
            for part in line.split():
                if part.startswith("usb://"):
                    parse_cups_usb_uri(part, info)
                    break
    return info
