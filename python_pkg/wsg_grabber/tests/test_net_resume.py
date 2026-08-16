"""Tests for resuming and discarding partial downloads."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from python_pkg.wsg_grabber import net
from python_pkg.wsg_grabber.constants import API_HEADERS
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
