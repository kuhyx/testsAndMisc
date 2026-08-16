"""Non-blocking PJL transport over the raw /dev/usb/lp* file descriptor.

Split out of :mod:`python_pkg.brother_printer.usb_query` to keep it under the
250-line cap. ``tests/test_usb_query_part2.py`` patches ``os``, ``select`` and
``time`` on this module, so those imports are load-bearing; the query callers
that stay in ``usb_query`` import these functions back, which is what keeps
``tests/test_usb_query.py`` patching them there.
"""

from __future__ import annotations

import contextlib
import os
import select
import time

# ── PJL over USB ─────────────────────────────────────────────────────


# The printer's fd is opened and kept non-blocking. usblp blocks indefinitely
# on a plain open() and on writes whenever the printer is not ready to talk -
# stuck mid-job, wedged, or simply asleep - so a blocking fd turns "the printer
# is unwell" into "this tool hangs forever", which is the worst possible answer
# when a status report is exactly what you wanted.


def _drain_buffer(fd: int) -> None:
    """Read and discard any stale data from the USB buffer."""
    with contextlib.suppress(OSError):
        while os.read(fd, 4096):
            pass


def _write_with_deadline(fd: int, data: bytes, deadline: float) -> bool:
    """Write all of data to a non-blocking fd. Returns False if the deadline passes.

    Args:
        fd: Non-blocking file descriptor for the printer.
        data: Bytes to send.
        deadline: Absolute monotonic-ish time (time.time()) to give up at.

    Returns:
        True when everything was written, False on timeout or write error.
    """
    sent = 0
    while sent < len(data):
        remaining = deadline - time.time()
        if remaining <= 0:
            return False
        try:
            sent += os.write(fd, data[sent:])
        except BlockingIOError:
            # Printer's buffer is full or it is not accepting data: wait for it
            # to become writable rather than spinning or blocking forever.
            _, writable, _ = select.select([], [fd], [], min(remaining, 0.5))
            if not writable:
                continue
        except OSError:
            return False
    return True


def _read_nonblocking(fd: int) -> bytes:
    """Read all currently available data from a non-blocking fd."""
    data = b""
    with contextlib.suppress(OSError):
        while True:
            chunk = os.read(fd, 4096)
            if not chunk:
                break
            data += chunk
    return data


def _wait_for_pjl_response(fd: int, deadline: float) -> bytes:
    """Poll fd until PJL data arrives or deadline expires."""
    response = b""
    while time.time() < deadline:
        remaining = deadline - time.time()
        if remaining <= 0:
            break
        readable, _, _ = select.select([fd], [], [], min(remaining, 1.0))
        if readable:
            response += _read_nonblocking(fd)
            if response and (b"=" in response or b"@PJL" in response):
                break
    return response


def pjl_query(fd: int, cmd: str, timeout_sec: float = 5.0) -> str:
    """Send a PJL command via raw fd and read the response.

    Args:
        fd: Non-blocking file descriptor for the printer.
        cmd: PJL command, e.g. "@PJL INFO STATUS".
        timeout_sec: Total budget for sending the command and reading the reply.

    Returns:
        The printer's reply, or "" if it did not answer in time. A silent
        printer is a normal outcome here, not an error: it happens whenever the
        printer is busy digesting a job.
    """
    deadline = time.time() + timeout_sec
    pjl_cmd = f"\x1b%-12345X@PJL\r\n{cmd}\r\n\x1b%-12345X"
    if not _write_with_deadline(fd, pjl_cmd.encode(), deadline):
        return ""
    response = _wait_for_pjl_response(fd, deadline)
    return response.decode("ascii", errors="replace")
