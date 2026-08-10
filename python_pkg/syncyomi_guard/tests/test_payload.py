"""Tests for the ``Backup`` protobuf reader.

The guarantee under test is that the counts are *true*. A decoder that silently
undercounts is worse than no guard at all, because it would report OK while the
library drained away.
"""

from __future__ import annotations

import pytest

from python_pkg.syncyomi_guard.payload import PayloadError, decode_payload
from python_pkg.syncyomi_guard.tests.conftest import (
    backup,
    encode_varint,
    length_delimited,
    manga,
    tag,
    varint_field,
)


def test_counts_every_top_level_field(healthy_payload: bytes) -> None:
    stats = decode_payload(healthy_payload)
    assert stats.manga == 10
    assert stats.chapters == 30
    assert stats.categories == 4
    assert stats.sources == 2
    assert stats.size_bytes == len(healthy_payload)


def test_chapters_come_from_field_16_not_the_title(stub_payload: bytes) -> None:
    """A title-only manga has zero chapters, not one.

    Field 3 is the title and field 16 is a chapter. Counting field 3 yields
    exactly one chapter per manga, which looks plausible in aggregate.
    """
    stats = decode_payload(manga(url="/manga/a", chapters=0, title="A Long Title"))
    assert stats.manga == 1
    assert stats.chapters == 0
    assert decode_payload(stub_payload).manga == 0


def test_the_2026_08_09_stub_reports_an_empty_library(stub_payload: bytes) -> None:
    """Sources present, library absent — the payload that overwrote the good one."""
    stats = decode_payload(stub_payload)
    assert stats.manga == 0
    assert stats.chapters == 0
    assert stats.categories == 0
    assert stats.sources == 2


def test_unknown_fields_of_every_wire_type_are_skipped() -> None:
    """Upstream may add fields; the guard must not break when it does."""
    payload = (
        manga(url="/manga/a", chapters=1)
        + varint_field(900, 12345)
        + tag(901, 5)
        + b"\x00\x01\x02\x03"
        + tag(902, 1)
        + b"\x00\x01\x02\x03\x04\x05\x06\x07"
        + length_delimited(903, b"opaque")
    )
    stats = decode_payload(payload)
    assert stats.manga == 1
    assert stats.chapters == 1


def test_unknown_wire_type_inside_a_manga_entry_is_skipped() -> None:
    """Exercises the non-length branch of the per-entry chapter scan."""
    body = length_delimited(2, b"/manga/a") + varint_field(8, 1) + tag(9, 5)
    payload = length_delimited(1, body + b"\x00\x01\x02\x03")
    assert decode_payload(payload).manga == 1


def test_empty_payload_is_rejected() -> None:
    with pytest.raises(PayloadError, match="empty"):
        decode_payload(b"")


def test_truncated_length_prefix_is_rejected() -> None:
    """A field claiming more bytes than exist is corruption, not a short read."""
    payload = tag(1, 2) + encode_varint(500) + b"too short"
    with pytest.raises(PayloadError, match="overruns"):
        decode_payload(payload)


def test_truncated_chapter_inside_a_manga_is_rejected() -> None:
    body = length_delimited(2, b"/manga/a") + tag(16, 2) + encode_varint(400) + b"xx"
    with pytest.raises(PayloadError, match="overruns manga entry"):
        decode_payload(length_delimited(1, body))


def test_unterminated_varint_is_rejected() -> None:
    with pytest.raises(PayloadError, match="unterminated"):
        decode_payload(b"\xff" * 12)


def test_varint_running_off_the_end_is_rejected() -> None:
    with pytest.raises(PayloadError, match="past end"):
        decode_payload(b"\xff\xff")


def test_unsupported_wire_type_is_rejected() -> None:
    with pytest.raises(PayloadError, match="unsupported wire type"):
        decode_payload(tag(1, 3))


def test_trailing_bytes_are_rejected() -> None:
    """Splice damage from page-level recovery must not decode as success."""
    payload = manga(url="/manga/a") + tag(2, 1) + b"\x00" * 4
    with pytest.raises(PayloadError, match="not fully consumed"):
        decode_payload(payload)


def test_describe_is_human_readable() -> None:
    text = decode_payload(backup(manga_count=2, chapters_each=1)).describe()
    assert "2 manga" in text
    assert "2 chapters" in text
