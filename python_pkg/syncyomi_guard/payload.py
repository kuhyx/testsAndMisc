"""Minimal protobuf reader for the Tachiyomi/Mihon ``Backup`` message.

Deliberately dependency-free. The alternative is vendoring Mihon's ``.proto``
files and a protobuf runtime, which would couple this guard to the app's schema
version — the guard has to keep working when upstream adds a field, because its
whole job is to run unattended and be trustworthy on the day something breaks.

Only the top-level field numbers are interpreted, and every unknown field is
skipped by wire type. Field numbers come from Mihon's ``BackupProto``:

===== ====================== =========================================
Field Meaning                Why the guard cares
===== ====================== =========================================
1     ``backupManga``        The library. A collapse here is the alarm.
2     ``backupCategories``   Lost silently on 2026-08-09 while manga survived.
16    ``chapters`` (nested)  Reading progress; catches a shallow restore.
101   ``backupSources``      Present even in a degraded payload, so it is
                             *not* evidence of health on its own.
===== ====================== =========================================
"""

from __future__ import annotations

from dataclasses import dataclass

_WIRE_VARINT = 0
_WIRE_64BIT = 1
_WIRE_LEN = 2
_WIRE_32BIT = 5

_FIELD_MANGA = 1
_FIELD_CATEGORIES = 2
_FIELD_CHAPTERS = 16
_FIELD_SOURCES = 101

# A varint wider than this is corruption, not a large number. Guards the decode
# loop against spinning on malformed input.
_MAX_VARINT_BYTES = 10


class PayloadError(ValueError):
    """Raised when the payload is not a decodable ``Backup`` message."""


@dataclass(frozen=True)
class PayloadStats:
    """What a payload actually contains, as opposed to what it claims.

    ``size_bytes`` is kept because it is the cheapest smoke test, but it is
    never the deciding signal: the 2026-08-09 stub was a perfectly well-formed
    protobuf message, just an almost empty one.
    """

    size_bytes: int
    manga: int
    categories: int
    chapters: int
    sources: int

    def describe(self) -> str:
        """Render a one-line human summary for logs and notifications."""
        return (
            f"{self.manga} manga, {self.chapters} chapters, "
            f"{self.categories} categories, {self.sources} sources "
            f"({self.size_bytes} bytes)"
        )


def _read_varint(buf: bytes, pos: int) -> tuple[int, int]:
    """Read a base-128 varint, returning the value and the new offset."""
    result = 0
    shift = 0
    start = pos
    while pos < len(buf):
        if pos - start >= _MAX_VARINT_BYTES:
            msg = f"varint at offset {start} is unterminated"
            raise PayloadError(msg)
        byte = buf[pos]
        pos += 1
        result |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return result, pos
        shift += 7
    msg = f"varint at offset {start} runs past end of payload"
    raise PayloadError(msg)


def _skip_field(buf: bytes, pos: int, wire_type: int) -> int:
    """Advance past one non-length-delimited field, returning the new offset.

    Length-delimited fields never reach here: both callers must inspect their
    contents, so they handle that wire type inline.
    """
    if wire_type == _WIRE_VARINT:
        _, pos = _read_varint(buf, pos)
        return pos
    if wire_type == _WIRE_64BIT:
        return pos + 8
    if wire_type == _WIRE_32BIT:
        return pos + 4
    msg = f"unsupported wire type {wire_type} at offset {pos}"
    raise PayloadError(msg)


def _count_chapters(entry: bytes) -> int:
    """Count ``chapters`` submessages inside one ``BackupManga`` entry.

    Chapters are field 16, not field 3 — field 3 is the title. Getting this
    wrong yields exactly one "chapter" per manga, which looks plausible enough
    to pass a careless review, so the distinction is load-bearing.
    """
    chapters = 0
    pos = 0
    while pos < len(entry):
        key, pos = _read_varint(entry, pos)
        field_number = key >> 3
        wire_type = key & 0x07
        if wire_type == _WIRE_LEN:
            length, pos = _read_varint(entry, pos)
            end = pos + length
            if end > len(entry):
                msg = "chapter field overruns manga entry"
                raise PayloadError(msg)
            if field_number == _FIELD_CHAPTERS:
                chapters += 1
            pos = end
        else:
            pos = _skip_field(entry, pos, wire_type)
    return chapters


def decode_payload(blob: bytes) -> PayloadStats:
    """Decode a ``Backup`` payload into verifiable counts.

    The payload must be consumed exactly: trailing bytes mean the message was
    truncated or spliced, which is precisely the corruption a page-level
    recovery can produce, so it is treated as an error rather than ignored.

    Raises:
        PayloadError: If the payload is empty, malformed, or not fully consumed.
    """
    if not blob:
        msg = "payload is empty"
        raise PayloadError(msg)

    manga = categories = chapters = sources = 0
    pos = 0
    while pos < len(blob):
        key, pos = _read_varint(blob, pos)
        field_number = key >> 3
        wire_type = key & 0x07
        if wire_type == _WIRE_LEN:
            length, pos = _read_varint(blob, pos)
            end = pos + length
            if end > len(blob):
                msg = f"field {field_number} overruns payload"
                raise PayloadError(msg)
            if field_number == _FIELD_MANGA:
                manga += 1
                chapters += _count_chapters(blob[pos:end])
            elif field_number == _FIELD_CATEGORIES:
                categories += 1
            elif field_number == _FIELD_SOURCES:
                sources += 1
            pos = end
        else:
            pos = _skip_field(blob, pos, wire_type)

    if pos != len(blob):
        msg = f"payload not fully consumed ({pos} of {len(blob)} bytes)"
        raise PayloadError(msg)

    return PayloadStats(
        size_bytes=len(blob),
        manga=manga,
        categories=categories,
        chapters=chapters,
        sources=sources,
    )
