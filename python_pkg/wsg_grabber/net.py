"""The only module that speaks HTTP.

Two hosts with different manners. ``a.4cdn.org`` is polite and supports
``If-Modified-Since``, so a steady-state rescan costs almost nothing.
``i.4cdn.org`` answered a bare request with 429 during development, and the
cookies it sets in reply (``__cf_bm``, ``_cfuvid``) live in the session jar --
which is why one long-lived :class:`requests.Session` is required rather than
merely convenient.
"""

from __future__ import annotations

import json

import requests

# Re-exported through __all__ so net.download / net.Transfer / net.digest_of /
# net.size_of keep working for downloader.py and test_net.py; the transfer
# machinery lives in _download to keep this module under the 250-line cap.
from python_pkg.wsg_grabber._download import (
    Transfer,
    digest_of,
    download,
    size_of,
)
from python_pkg.wsg_grabber.constants import (
    API_HEADERS,
    CONNECT_TIMEOUT_S,
    MAX_JSON_BYTES,
    READ_TIMEOUT_S,
)
from python_pkg.wsg_grabber.models import JsonResponse

__all__ = [
    "Transfer",
    "build_session",
    "digest_of",
    "download",
    "get_json",
    "size_of",
]


_TIMEOUT = (CONNECT_TIMEOUT_S, READ_TIMEOUT_S)
_OK = 200
_PARTIAL = 206
_NOT_MODIFIED = 304
_NOT_FOUND = 404
_GONE = 410
_RANGE_NOT_SATISFIABLE = 416
_TOO_MANY = 429
_SERVER_ERROR = 500


def build_session() -> requests.Session:
    """Return a session configured for the API host.

    Returns:
        requests.Session: Caller owns it and must close it.
    """
    session = requests.Session()
    session.headers.update(API_HEADERS)
    return session


def get_json(
    session: requests.Session,
    url: str,
    last_modified: str | None = None,
) -> JsonResponse:
    """Fetch and decode a JSON endpoint, conditionally when possible.

    Args:
        session: Shared session.
        url: Absolute API URL.
        last_modified: Previously seen ``Last-Modified`` value, echoed back as
            ``If-Modified-Since`` so an unchanged thread costs a 304.

    Returns:
        JsonResponse: Decoded payload, or a flag explaining why there is none.
    """
    headers = {"If-Modified-Since": last_modified} if last_modified else {}
    response = session.get(url, headers=headers, timeout=_TIMEOUT)
    status = response.status_code
    if status == _NOT_MODIFIED:
        return JsonResponse(
            payload=None,
            last_modified=last_modified,
            not_modified=True,
            not_found=False,
        )
    if status in (_NOT_FOUND, _GONE):
        return JsonResponse(
            payload=None,
            last_modified=None,
            not_modified=False,
            not_found=True,
        )
    response.raise_for_status()
    body = response.content[: MAX_JSON_BYTES + 1]
    if len(body) > MAX_JSON_BYTES:
        msg = f"API response exceeded {MAX_JSON_BYTES} bytes"
        raise ValueError(msg)
    return JsonResponse(
        payload=json.loads(body),
        last_modified=response.headers.get("Last-Modified"),
        not_modified=False,
        not_found=False,
    )
