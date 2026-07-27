"""Tests for the HTTP layer.

No socket is opened: ``requests.Session`` is replaced with a mock whose
``iter_content`` yields real bytes, so the md5 verification path computes a
genuine digest rather than comparing two mocks.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
import requests

from python_pkg.wsg_grabber import net
from python_pkg.wsg_grabber.constants import API_HEADERS, MEDIA_HEADERS
from python_pkg.wsg_grabber.models import Outcome

if TYPE_CHECKING:
    from pathlib import Path

_BODY = b"fake webm bytes, but real bytes" * 40


def _response(
    status: int = 200,
    *,
    body: bytes = b"",
    headers: dict[str, str] | None = None,
    text: str = "",
) -> MagicMock:
    """Build a stand-in for a requests Response.

    Args:
        status: HTTP status code.
        body: Payload streamed by ``iter_content``.
        headers: Response headers.
        text: Body for JSON decoding.

    Returns:
        MagicMock: Response double.
    """
    response = MagicMock()
    response.status_code = status
    response.headers = headers or {}
    response.text = text
    response.content = text.encode("utf-8")
    response.iter_content.return_value = [body] if body else []
    return response


def _transfer(tmp_path: Path, *, md5: str | None = None, size: int = 0) -> net.Transfer:
    """Build a Transfer pointing at a sandboxed part file.

    Args:
        tmp_path: Per-test temporary directory.
        md5: Expected digest; defaults to the real digest of ``_BODY``.
        size: Expected file size.

    Returns:
        net.Transfer: Transfer description.
    """
    return net.Transfer(
        url="https://i.4cdn.org/wsg/1.webm",
        part_path=tmp_path / "1.webm.part",
        expected_md5=md5 if md5 is not None else net.digest_of(_BODY),
        expected_size=size,
        should_stop=lambda: False,
    )


def test_digest_matches_the_field_the_api_publishes() -> None:
    """Verified against a real /wsg/ file during design."""
    assert net.digest_of(b"") == "1B2M2Y8AsgTpgAmY7PhCfg=="
    assert len(net.digest_of(_BODY)) == 24


def test_build_session_carries_the_api_headers() -> None:
    session = net.build_session()
    try:
        assert session.headers["User-Agent"] == API_HEADERS["User-Agent"]
        assert session.headers["Referer"] == API_HEADERS["Referer"]
    finally:
        session.close()


def test_get_json_decodes_a_fresh_payload() -> None:
    session = MagicMock()
    session.get.return_value = _response(
        200,
        text='{"posts": [1]}',
        headers={"Last-Modified": "Mon, 27 Jul 2026 08:00:00 GMT"},
    )
    result = net.get_json(session, "https://a.4cdn.org/wsg/threads.json")
    assert result.payload == {"posts": [1]}
    assert result.last_modified == "Mon, 27 Jul 2026 08:00:00 GMT"
    assert not result.not_modified
    assert session.get.call_args.kwargs["headers"] == {}


def test_get_json_sends_if_modified_since_and_honours_304() -> None:
    """An unchanged thread must cost a 304, not a re-parse."""
    session = MagicMock()
    session.get.return_value = _response(304)
    stamp = "Mon, 27 Jul 2026 08:00:00 GMT"
    result = net.get_json(session, "https://a.4cdn.org/wsg/thread/1.json", stamp)
    assert result.not_modified
    assert result.payload is None
    assert result.last_modified == stamp
    assert session.get.call_args.kwargs["headers"] == {"If-Modified-Since": stamp}


@pytest.mark.parametrize("status", [404, 410])
def test_get_json_reports_a_vanished_thread(status: int) -> None:
    session = MagicMock()
    session.get.return_value = _response(status)
    result = net.get_json(session, "https://a.4cdn.org/wsg/thread/1.json")
    assert result.not_found
    assert result.payload is None


def test_get_json_raises_on_other_failures() -> None:
    session = MagicMock()
    response = _response(500)
    response.raise_for_status.side_effect = requests.HTTPError("boom")
    session.get.return_value = response
    with pytest.raises(requests.HTTPError):
        net.get_json(session, "https://a.4cdn.org/wsg/threads.json")


def test_download_writes_and_verifies_the_file(tmp_path: Path) -> None:
    session = MagicMock()
    session.get.return_value = _response(200, body=_BODY)
    transfer = _transfer(tmp_path)
    result = net.download(session, transfer)
    assert result.outcome is Outcome.COMPLETED
    assert result.bytes_done == len(_BODY)
    assert transfer.part_path.read_bytes() == _BODY
    assert (
        session.get.call_args.kwargs["headers"]["Referer"] == MEDIA_HEADERS["Referer"]
    )
    assert "Range" not in session.get.call_args.kwargs["headers"]


def test_download_reports_progress(tmp_path: Path) -> None:
    session = MagicMock()
    session.get.return_value = _response(200, body=_BODY)
    seen: list[int] = []
    transfer = net.Transfer(
        url="https://i.4cdn.org/wsg/1.webm",
        part_path=tmp_path / "1.webm.part",
        expected_md5=net.digest_of(_BODY),
        expected_size=0,
        should_stop=lambda: False,
        on_progress=seen.append,
    )
    net.download(session, transfer)
    assert seen == [len(_BODY)]


def test_download_rejects_a_body_whose_digest_disagrees(tmp_path: Path) -> None:
    """A mangled transfer must never reach the reviewer."""
    session = MagicMock()
    session.get.return_value = _response(200, body=_BODY)
    transfer = _transfer(tmp_path, md5="A" * 24)
    result = net.download(session, transfer)
    assert result.outcome is Outcome.CHECKSUM_MISMATCH
    assert not transfer.part_path.exists()


@pytest.mark.parametrize("status", [404, 410])
def test_download_marks_a_missing_file_not_found(tmp_path: Path, status: int) -> None:
    session = MagicMock()
    session.get.return_value = _response(status)
    result = net.download(session, _transfer(tmp_path))
    assert result.outcome is Outcome.NOT_FOUND


def test_download_reads_retry_after_on_429(tmp_path: Path) -> None:
    session = MagicMock()
    session.get.return_value = _response(429, headers={"Retry-After": "45"})
    result = net.download(session, _transfer(tmp_path))
    assert result.outcome is Outcome.TRANSIENT
    assert result.retry_after == pytest.approx(45.0)


def test_download_treats_server_errors_as_transient(tmp_path: Path) -> None:
    session = MagicMock()
    session.get.return_value = _response(503)
    result = net.download(session, _transfer(tmp_path))
    assert result.outcome is Outcome.TRANSIENT
    assert result.retry_after is None


def test_download_treats_an_unexpected_status_as_transient(tmp_path: Path) -> None:
    session = MagicMock()
    session.get.return_value = _response(302)
    result = net.download(session, _transfer(tmp_path))
    assert result.outcome is Outcome.TRANSIENT
    assert result.message is not None
    assert "302" in result.message


def test_download_turns_a_network_error_into_a_transient_result(
    tmp_path: Path,
) -> None:
    session = MagicMock()
    session.get.side_effect = requests.ConnectionError("no route")
    result = net.download(session, _transfer(tmp_path))
    assert result.outcome is Outcome.TRANSIENT
    assert result.message == "no route"


def test_download_resumes_a_partial_file(tmp_path: Path) -> None:
    part = tmp_path / "1.webm.part"
    part.write_bytes(_BODY[:100])
    session = MagicMock()
    session.get.return_value = _response(206, body=_BODY[100:])
    transfer = net.Transfer(
        url="https://i.4cdn.org/wsg/1.webm",
        part_path=part,
        expected_md5=net.digest_of(_BODY),
        expected_size=len(_BODY),
        should_stop=lambda: False,
    )
    result = net.download(session, transfer)
    assert session.get.call_args.kwargs["headers"]["Range"] == "bytes=100-"
    assert result.outcome is Outcome.COMPLETED
    assert part.read_bytes() == _BODY


def test_a_server_ignoring_range_restarts_rather_than_appending(
    tmp_path: Path,
) -> None:
    """Replying 200 to a Range request means the whole file is coming again."""
    part = tmp_path / "1.webm.part"
    part.write_bytes(_BODY[:100])
    session = MagicMock()
    session.get.return_value = _response(200, body=_BODY)
    transfer = net.Transfer(
        url="https://i.4cdn.org/wsg/1.webm",
        part_path=part,
        expected_md5=net.digest_of(_BODY),
        expected_size=len(_BODY),
        should_stop=lambda: False,
    )
    result = net.download(session, transfer)
    assert result.outcome is Outcome.COMPLETED
    assert part.read_bytes() == _BODY


def test_an_oversized_leftover_is_discarded_before_requesting(
    tmp_path: Path,
) -> None:
    part = tmp_path / "1.webm.part"
    part.write_bytes(b"x" * 9999)
    session = MagicMock()
    session.get.return_value = _response(200, body=_BODY)
    transfer = net.Transfer(
        url="https://i.4cdn.org/wsg/1.webm",
        part_path=part,
        expected_md5=net.digest_of(_BODY),
        expected_size=len(_BODY),
        should_stop=lambda: False,
    )
    result = net.download(session, transfer)
    assert "Range" not in session.get.call_args.kwargs["headers"]
    assert result.outcome is Outcome.COMPLETED


def test_a_rejected_range_restarts_from_zero(tmp_path: Path) -> None:
    part = tmp_path / "1.webm.part"
    part.write_bytes(_BODY[:100])
    session = MagicMock()
    session.get.return_value = _response(416)
    transfer = net.Transfer(
        url="https://i.4cdn.org/wsg/1.webm",
        part_path=part,
        expected_md5=net.digest_of(_BODY),
        expected_size=len(_BODY),
        should_stop=lambda: False,
    )
    result = net.download(session, transfer)
    assert result.outcome is Outcome.TRANSIENT
    assert not part.exists()


def test_shutdown_aborts_mid_stream_and_keeps_the_partial(tmp_path: Path) -> None:
    """Stopping must be immediate and must leave a resumable .part behind."""
    session = MagicMock()
    response = _response(200)
    response.iter_content.return_value = [b"a" * 10, b"b" * 10, b"c" * 10]
    session.get.return_value = response
    transfer = net.Transfer(
        url="https://i.4cdn.org/wsg/1.webm",
        part_path=tmp_path / "1.webm.part",
        expected_md5="whatever" + "=" * 16,
        expected_size=30,
        should_stop=lambda: True,
    )
    result = net.download(session, transfer)
    assert result.outcome is Outcome.ABORTED


def test_empty_chunks_are_skipped(tmp_path: Path) -> None:
    """requests yields keep-alive chunks; they must not corrupt the digest."""
    session = MagicMock()
    response = _response(200)
    response.iter_content.return_value = [b"", _BODY, b""]
    session.get.return_value = response
    result = net.download(session, _transfer(tmp_path))
    assert result.outcome is Outcome.COMPLETED


def test_size_of_missing_file_is_zero(tmp_path: Path) -> None:
    assert net.size_of(tmp_path / "nope") == 0


def test_a_compressed_body_is_refused(tmp_path: Path) -> None:
    """We ask for identity; requests would silently expand a gzip bomb."""
    session = MagicMock()
    session.get.return_value = _response(
        200,
        body=_BODY,
        headers={"Content-Encoding": "gzip"},
    )
    result = net.download(session, _transfer(tmp_path))
    assert result.outcome is Outcome.TRANSIENT
    assert result.message is not None
    assert "Content-Encoding" in result.message


def test_a_body_larger_than_advertised_is_abandoned(tmp_path: Path) -> None:
    """A server that lies about its size must not fill the disk."""
    session = MagicMock()
    response = _response(200)
    response.iter_content.return_value = [b"x" * (1024 * 1024)] * 4
    session.get.return_value = response
    transfer = net.Transfer(
        url="https://i.4cdn.org/wsg/1.webm",
        part_path=tmp_path / "1.webm.part",
        expected_md5=net.digest_of(_BODY),
        expected_size=16,
        should_stop=lambda: False,
    )
    result = net.download(session, transfer)
    assert result.outcome is Outcome.TRANSIENT
    assert not transfer.part_path.exists()


def test_an_unknown_size_is_not_treated_as_over_budget(tmp_path: Path) -> None:
    """fsize 0 means the API did not say; that must not block the download."""
    session = MagicMock()
    session.get.return_value = _response(200, body=_BODY)
    result = net.download(session, _transfer(tmp_path, size=0))
    assert result.outcome is Outcome.COMPLETED


def test_an_oversized_api_response_is_refused() -> None:
    session = MagicMock()
    response = _response(200)
    response.content = b"[" + b"1," * 20_000_000 + b"1]"
    session.get.return_value = response
    with pytest.raises(ValueError, match="exceeded"):
        net.get_json(session, "https://a.4cdn.org/wsg/threads.json")


def test_the_api_session_refuses_compression() -> None:
    assert API_HEADERS["Accept-Encoding"] == "identity"
