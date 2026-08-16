"""Streaming one media file to disk, with resume and verification.

Split out of :mod:`python_pkg.wsg_grabber.net` to keep that module under the
250-line cap. ``net`` still owns the session and the JSON endpoints; everything
about pulling bytes from ``i.4cdn.org`` and deciding whether to trust them
lives here.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
import hashlib
from typing import TYPE_CHECKING

import requests

from python_pkg.wsg_grabber._reject import classify, size_of
from python_pkg.wsg_grabber.constants import (
    CHUNK_BYTES,
    CONNECT_TIMEOUT_S,
    MEDIA_HEADERS,
    READ_TIMEOUT_S,
    SIZE_SLACK_BYTES,
)
from python_pkg.wsg_grabber.models import DownloadResult, Outcome
from python_pkg.wsg_grabber.scanner import resume_plan

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

_TIMEOUT = (CONNECT_TIMEOUT_S, READ_TIMEOUT_S)
_OK = 200
_PARTIAL = 206
_NOT_FOUND = 404
_GONE = 410
_RANGE_NOT_SATISFIABLE = 416
_TOO_MANY = 429
_SERVER_ERROR = 500


def digest_of(payload: bytes) -> str:
    """Return the base64 MD5 the API uses to identify a file.

    MD5 here is 4chan's content identifier, not a security control, hence
    ``usedforsecurity=False``.

    Args:
        payload: Full file contents.

    Returns:
        str: 24-character base64 digest.
    """
    digest = hashlib.md5(payload, usedforsecurity=False).digest()
    return base64.b64encode(digest).decode("ascii")


@dataclass(frozen=True, slots=True)
class Transfer:
    """Everything one download needs, bundled to stay within the arg limit."""

    url: str
    part_path: Path
    expected_md5: str
    expected_size: int
    should_stop: Callable[[], bool]
    on_progress: Callable[[int], None] | None = None


def download(session: requests.Session, transfer: Transfer) -> DownloadResult:
    """Stream a file to disk, resuming where possible and verifying the result.

    The bytes are checked against the API's md5 before the download counts as
    finished, so a truncated or mangled transfer can never reach the reviewer.

    Args:
        session: Shared session.
        transfer: What to fetch and where to put it.

    Returns:
        DownloadResult: Outcome plus the byte count now on disk.
    """
    plan = resume_plan(size_of(transfer.part_path), transfer.expected_size)
    if plan.discard:
        transfer.part_path.unlink(missing_ok=True)
    headers = dict(MEDIA_HEADERS)
    if plan.offset:
        headers["Range"] = f"bytes={plan.offset}-"

    try:
        return _stream(session, transfer, headers, plan.offset)
    except requests.RequestException as exc:
        return DownloadResult(
            outcome=Outcome.TRANSIENT,
            bytes_done=size_of(transfer.part_path),
            message=str(exc),
        )


def _stream(
    session: requests.Session,
    transfer: Transfer,
    headers: dict[str, str],
    offset: int,
) -> DownloadResult:
    """Perform the request and write the body out.

    Args:
        session: Shared session.
        transfer: What to fetch and where to put it.
        headers: Media headers, possibly carrying a ``Range``.
        offset: Byte offset requested; zero for a fresh download.

    Returns:
        DownloadResult: Outcome plus the byte count now on disk.
    """
    response = session.get(
        transfer.url,
        headers=headers,
        timeout=_TIMEOUT,
        stream=True,
    )
    rejection = classify(response, transfer)
    if rejection is not None:
        return rejection

    # A server that ignores Range replies 200 with the whole file, so anything
    # already on disk has to be thrown away rather than appended to.
    append = offset > 0 and response.status_code == _PARTIAL
    written = _write_body(response, transfer, append=append)
    if written is None:
        return DownloadResult(
            outcome=Outcome.ABORTED,
            bytes_done=size_of(transfer.part_path),
        )
    if _over_budget(written, transfer.expected_size):
        transfer.part_path.unlink(missing_ok=True)
        return DownloadResult(
            outcome=Outcome.TRANSIENT,
            bytes_done=0,
            message=f"body exceeded the advertised {transfer.expected_size} bytes",
        )

    payload = transfer.part_path.read_bytes()
    if digest_of(payload) != transfer.expected_md5:
        transfer.part_path.unlink(missing_ok=True)
        return DownloadResult(
            outcome=Outcome.CHECKSUM_MISMATCH,
            bytes_done=0,
            message="md5 did not match the value published by the API",
        )
    return DownloadResult(outcome=Outcome.COMPLETED, bytes_done=len(payload))


def _over_budget(written: int, expected: int) -> bool:
    """Report whether a transfer outgrew the size the API advertised.

    Without this a server that lies about Content-Length can write until the
    disk is full; the md5 check alone does not help, because whoever serves the
    bytes also publishes the digest.

    Args:
        written: Bytes now on disk.
        expected: Size the API declared; zero means it did not say.

    Returns:
        bool: True when the transfer should be abandoned.
    """
    if expected <= 0:
        return False
    return written > expected + SIZE_SLACK_BYTES


def _write_body(
    response: requests.Response,
    transfer: Transfer,
    *,
    append: bool,
) -> int | None:
    """Write the response body to the part file.

    Args:
        response: Streamed response.
        transfer: What is being fetched.
        append: Whether to continue an existing part file.

    Returns:
        int | None: Bytes written, or None when shutdown interrupted it.
    """
    mode = "ab" if append else "wb"
    done = size_of(transfer.part_path) if append else 0
    with transfer.part_path.open(mode) as handle:
        for chunk in response.iter_content(chunk_size=CHUNK_BYTES):
            if transfer.should_stop():
                return None
            if not chunk:
                continue
            handle.write(chunk)
            done += len(chunk)
            if transfer.on_progress is not None:
                transfer.on_progress(done)
            if _over_budget(done, transfer.expected_size):
                return done
    return done
