"""Shared protobuf builders for the guard's tests.

The tests construct real ``Backup`` wire format rather than mocking the decoder.
A mock would happily agree with a decoder that counts the wrong field number,
which is the specific bug this package had while being written (chapters are
field 16; field 3 is the title, and counting it yields exactly one "chapter"
per manga).
"""

from __future__ import annotations

import pytest

_WIRE_VARINT = 0
_WIRE_LEN = 2


def encode_varint(value: int) -> bytes:
    """Encode ``value`` as a base-128 varint."""
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


def tag(field_number: int, wire_type: int) -> bytes:
    """Encode a protobuf field tag."""
    return encode_varint((field_number << 3) | wire_type)


def length_delimited(field_number: int, payload: bytes) -> bytes:
    """Encode a length-delimited field."""
    return tag(field_number, _WIRE_LEN) + encode_varint(len(payload)) + payload


def varint_field(field_number: int, value: int) -> bytes:
    """Encode a varint field."""
    return tag(field_number, _WIRE_VARINT) + encode_varint(value)


def chapter(url: str = "/chapter/x") -> bytes:
    """Build one ``chapters`` submessage (field 16 of ``BackupManga``)."""
    return length_delimited(16, length_delimited(1, url.encode()))


def manga(*, url: str = "/manga/x", chapters: int = 0, title: str = "T") -> bytes:
    """Build one ``BackupManga`` entry (field 1 of ``Backup``)."""
    body = length_delimited(2, url.encode()) + length_delimited(3, title.encode())
    body += b"".join(chapter(f"{url}/c{i}") for i in range(chapters))
    return length_delimited(1, body)


def category(name: str) -> bytes:
    """Build one ``BackupCategory`` entry (field 2 of ``Backup``)."""
    return length_delimited(2, length_delimited(1, name.encode()))


def source(name: str = "MangaDex") -> bytes:
    """Build one ``BackupSource`` entry (field 101 of ``Backup``)."""
    return length_delimited(101, length_delimited(1, name.encode()))


def backup(
    *,
    manga_count: int = 0,
    chapters_each: int = 0,
    categories: int = 0,
    sources: int = 0,
) -> bytes:
    """Build a whole ``Backup`` message with the requested shape."""
    parts = [
        manga(url=f"/manga/{i}", chapters=chapters_each) for i in range(manga_count)
    ]
    parts += [category(f"cat{i}") for i in range(categories)]
    parts += [source(f"src{i}") for i in range(sources)]
    return b"".join(parts)


@pytest.fixture
def healthy_payload() -> bytes:
    """A payload standing in for a normal library."""
    return backup(manga_count=10, chapters_each=3, categories=4, sources=2)


@pytest.fixture
def stub_payload() -> bytes:
    """The 2026-08-09 failure shape: sources survive, the library does not."""
    return backup(manga_count=0, categories=0, sources=2)
