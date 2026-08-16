"""Deciding whether a media response can be trusted at all.

Split out of :mod:`python_pkg.wsg_grabber._download` to keep it under the
250-line cap. This is pure classification of a status line and headers into an
:class:`Outcome`; it never touches the body.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from python_pkg.wsg_grabber.models import DownloadResult, Outcome
from python_pkg.wsg_grabber.scanner import parse_retry_after

if TYPE_CHECKING:
    from pathlib import Path

    import requests

    from python_pkg.wsg_grabber._download import Transfer

_OK = 200
_PARTIAL = 206
_NOT_FOUND = 404
_GONE = 410
_RANGE_NOT_SATISFIABLE = 416
_TOO_MANY = 429
_SERVER_ERROR = 500


def size_of(path: Path) -> int:
    """Return the size of *path*, or zero when it does not exist.

    Args:
        path: File to measure.

    Returns:
        int: Size in bytes.
    """
    return path.stat().st_size if path.exists() else 0


def classify(
    response: requests.Response,
    transfer: Transfer,
) -> DownloadResult | None:
    """Classify a non-success status, if any.

    Args:
        response: The (streamed) response.
        transfer: The transfer being attempted.

    Returns:
        DownloadResult | None: None when the response is usable.
    """
    status = response.status_code
    if status in (_NOT_FOUND, _GONE):
        transfer.part_path.unlink(missing_ok=True)
        return DownloadResult(
            outcome=Outcome.NOT_FOUND,
            bytes_done=0,
            message=f"HTTP {status}",
        )
    encoding = response.headers.get("Content-Encoding", "identity")
    if encoding != "identity":
        # We asked for identity. A compressed body means the far side is not
        # playing by the rules, and requests would silently expand it -- a
        # 200 KB response can decode to 200 MB, and the md5 would still match
        # because the same party published it.
        return DownloadResult(
            outcome=Outcome.TRANSIENT,
            bytes_done=size_of(transfer.part_path),
            message=f"refused Content-Encoding: {encoding}",
        )
    if status == _RANGE_NOT_SATISFIABLE:
        # The leftover part is longer than the file actually is; start over.
        transfer.part_path.unlink(missing_ok=True)
        return DownloadResult(
            outcome=Outcome.TRANSIENT,
            bytes_done=0,
            message="range rejected; restarting",
        )
    if status == _TOO_MANY or status >= _SERVER_ERROR:
        return DownloadResult(
            outcome=Outcome.TRANSIENT,
            bytes_done=size_of(transfer.part_path),
            retry_after=parse_retry_after(response.headers.get("Retry-After")),
            message=f"HTTP {status}",
        )
    if status not in (_OK, _PARTIAL):
        return DownloadResult(
            outcome=Outcome.TRANSIENT,
            bytes_done=size_of(transfer.part_path),
            message=f"unexpected HTTP {status}",
        )
    return None
