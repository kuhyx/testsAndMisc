"""Tests for python_pkg.fm24_searcher.binary_parser."""

from __future__ import annotations

import struct
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
import zstandard

from python_pkg.fm24_searcher.binary_parser import (
    ATTR_BLOCK_MAP,
    FMF_MAGIC,
    REC_SEP,
    TAD_MAGIC,
    ZSTD_MAGIC,
    _attrs_from_block,
    _decompress_multiframe,
    _decompress_single,
    _dob_from_bytes,
    _enrich_with_attributes,
    _find_all_attr_blocks,
    _find_name_boundaries,
    _is_valid_attr_block,
    _is_valid_name,
    _pass1_separator_walk,
    _pass2_regex_scan,
    _try_extract_player,
    decompress_file,
    parse_people_db,
    search_players,
)
from python_pkg.fm24_searcher.models import Player

if TYPE_CHECKING:
    from pathlib import Path


def _zstd_compress(data: bytes) -> bytes:
    """Compress data with zstd for test fixtures."""
    cctx = zstandard.ZstdCompressor()
    result: bytes = cctx.compress(data)
    return result


def _make_tad(payload: bytes) -> bytes:
    """Create a TAD-formatted blob."""
    return TAD_MAGIC + _zstd_compress(payload)


def _make_player_record(
    name: str,
    *,
    day_of_year: int = 180,
    year: int = 1995,
    personality: bytes = b"\x0a\x0b\x0c\x0d\x0e\x0f\x10\x05",
    prefix: int = 0x00,
) -> bytes:
    """Build a minimal binary player record.

    Layout: 0x00 + uint32 name_len + name_utf8 + DOB(4) +
    5 flag bytes + 2 bytes "nat_id" + 2 zeros + 4 bytes "ref" +
    8 personality bytes.
    """
    name_bytes = name.encode("utf-8")
    rec = bytes([prefix])
    rec += struct.pack("<I", len(name_bytes))
    rec += name_bytes
    rec += struct.pack("<H", day_of_year)  # DOB day
    rec += struct.pack("<H", year)  # DOB year
    rec += b"\x07\x03\x0b\x06\x0c"  # 5 flag bytes
    rec += b"\x8b\x00"  # +9: uint16 nat_id (ignored)
    rec += b"\x00\x00"  # +11-12: zeros
    rec += b"\x01\x03\x00\x00"  # +13-16: ref_id (ignored)
    rec += personality  # +17-24: 8 personality bytes
    return rec


class TestDecompressSingle:
    """_decompress_single tests."""

    def test_valid(self) -> None:
        payload = b"hello world"
        raw = _make_tad(payload)
        assert _decompress_single(raw) == payload

    def test_bad_magic(self) -> None:
        with pytest.raises(ValueError, match="Expected TAD magic"):
            _decompress_single(b"\x00" * 8 + b"data")


class TestDecompressMultiframe:
    """_decompress_multiframe tests."""

    def test_multiple_frames(self) -> None:
        frame1 = _zstd_compress(b"frame1")
        frame2 = _zstd_compress(b"frame2")
        raw = b"header" + frame1 + b"gap" + frame2
        result = _decompress_multiframe(raw)
        assert b"frame1" in result
        assert b"frame2" in result

    def test_no_frames(self) -> None:
        result = _decompress_multiframe(b"no zstd here")
        assert result == []

    def test_corrupt_frame_skipped(self) -> None:
        # Put the magic bytes but no valid zstd data after.
        raw = ZSTD_MAGIC + b"\x00\x00\x00"
        result = _decompress_multiframe(raw)
        assert result == []


class TestDecompressFile:
    """decompress_file tests."""

    def test_tad_file(self, tmp_path: Path) -> None:
        p = tmp_path / "test.dat"
        p.write_bytes(_make_tad(b"payload"))
        assert decompress_file(p) == b"payload"

    def test_fmf_file(self, tmp_path: Path) -> None:
        frame = _zstd_compress(b"content")
        raw = FMF_MAGIC + b"\x00" * 10 + frame
        p = tmp_path / "test.dat"
        p.write_bytes(raw)
        result = decompress_file(p)
        assert isinstance(result, list)
        assert b"content" in result

    def test_unknown_format(self, tmp_path: Path) -> None:
        p = tmp_path / "test.dat"
        p.write_bytes(b"\xff" * 20)
        with pytest.raises(ValueError, match="Unknown file format"):
            decompress_file(p)


class TestDobFromBytes:
    """_dob_from_bytes tests."""

    def test_valid_dob(self) -> None:
        data = struct.pack("<HH", 180, 1995)
        assert _dob_from_bytes(data, 0) == "1995-06-29"

    def test_jan_first(self) -> None:
        data = struct.pack("<HH", 1, 2000)
        assert _dob_from_bytes(data, 0) == "2000-01-01"

    def test_dec_31(self) -> None:
        data = struct.pack("<HH", 365, 2000)
        assert _dob_from_bytes(data, 0) == "2000-12-30"

    def test_invalid_year_below(self) -> None:
        data = struct.pack("<HH", 180, 1800)
        assert _dob_from_bytes(data, 0) == ""

    def test_invalid_year_above(self) -> None:
        data = struct.pack("<HH", 180, 2020)
        assert _dob_from_bytes(data, 0) == ""

    def test_invalid_day_zero(self) -> None:
        data = struct.pack("<HH", 0, 1995)
        assert _dob_from_bytes(data, 0) == ""

    def test_invalid_day_too_large(self) -> None:
        data = struct.pack("<HH", 400, 1995)
        assert _dob_from_bytes(data, 0) == ""

    def test_leap_year_day_366(self) -> None:
        data = struct.pack("<HH", 366, 2000)
        assert _dob_from_bytes(data, 0) == "2000-12-31"

    def test_overflow_day_366_non_leap(self) -> None:
        # Day 366 in a non-leap year overflows to next year.
        data = struct.pack("<HH", 366, 1999)
        # timedelta(365) from Jan 1 1999 → Jan 1 2000.
        assert _dob_from_bytes(data, 0) == "2000-01-01"

    def test_date_creation_raises(self) -> None:
        """Cover except (ValueError, OverflowError) branch (lines 115-116)."""
        data = struct.pack("<HH", 180, 1995)
        with patch("python_pkg.fm24_searcher.binary_parser.datetime") as mock_dt:
            mock_dt.date.side_effect = OverflowError("forced")
            assert _dob_from_bytes(data, 0) == ""

    def test_with_offset(self) -> None:
        prefix = b"\xff\xff"
        data = prefix + struct.pack("<HH", 1, 2005)
        assert _dob_from_bytes(data, 2) == "2005-01-01"


class TestFindNameBoundaries:
    """_find_name_boundaries tests."""

    def test_found(self) -> None:
        name = "John Smith"
        name_bytes = name.encode("utf-8")
        data = b"\x00" + struct.pack("<I", len(name_bytes)) + name_bytes
        # name_pos = index of 'J' = 5
        result = _find_name_boundaries(data, 5)
        assert result is not None
        assert result[0] == name
        assert result[1] == 1  # offset of length prefix
        assert result[2] == 5 + len(name_bytes)  # name end

    def test_not_found(self) -> None:
        data = b"\xff" * 100
        assert _find_name_boundaries(data, 50) is None

    def test_invalid_utf8(self) -> None:
        raw_name = b"\x80\x81\x82\x83"
        data = b"\x00" + struct.pack("<I", len(raw_name)) + raw_name
        assert _find_name_boundaries(data, 5) is None

    def test_name_too_short(self) -> None:
        name = b"AB"  # 2 bytes, below _BOUNDARY_MIN_NAME_LEN (3)
        data = b"\x00" + struct.pack("<I", len(name)) + name
        assert _find_name_boundaries(data, 5) is None

    def test_offset_too_small(self) -> None:
        # name_pos at 0 means off = 0 - back - 4 < 0.
        assert _find_name_boundaries(b"\x00" * 10, 0) is None

    def test_non_printable_name(self) -> None:
        name = "Test\x01Name"
        name_bytes = name.encode("utf-8")
        data = b"\x00" + struct.pack("<I", len(name_bytes)) + name_bytes
        assert _find_name_boundaries(data, 5) is None

    def test_name_pos_outside_range(self) -> None:
        """Valid name_len found but name_pos not in [ns, ne) (137→128)."""
        # Place valid length=5 at offset 10.
        data = b"\xff" * 10 + struct.pack("<I", 5) + b"Hello" + b"\xff" * 50
        # name_pos=30. At back=16, off=10. ns=14, ne=19. 14<=30<19? No.
        assert _find_name_boundaries(data, 30) is None


class TestIsValidName:
    """_is_valid_name tests."""

    def test_valid(self) -> None:
        data = b"John Smith"
        assert _is_valid_name(data, 0, 10) == "John Smith"

    def test_beyond_data(self) -> None:
        data = b"Short"
        assert _is_valid_name(data, 0, 100) == ""

    def test_invalid_utf8(self) -> None:
        data = b"\x80\x81\x82"
        assert _is_valid_name(data, 0, 3) == ""

    def test_no_alpha(self) -> None:
        data = b"123 456"
        assert _is_valid_name(data, 0, 7) == ""

    def test_non_printable(self) -> None:
        data = b"Test\x00Name"
        assert _is_valid_name(data, 0, len(data)) == ""

    def test_with_offset(self) -> None:
        data = b"\xff\xffJohn"
        assert _is_valid_name(data, 2, 4) == "John"

    def test_trailing_non_alpha_rejected(self) -> None:
        """Names ending with punctuation like '<' are rejected."""
        data = b"John Smith<"
        assert _is_valid_name(data, 0, len(data)) == ""


class TestTryExtractPlayer:
    """_try_extract_player tests."""

    def test_valid_record(self) -> None:
        rec = _make_player_record("John Smith", day_of_year=180, year=1995)
        padding = b"\x00" * 10  # trailing space
        result = _try_extract_player(rec + padding, 0)
        assert result is not None
        player, _ne = result
        assert player.name == "John Smith"
        assert player.date_of_birth == "1995-06-29"
        assert player.uid == 0  # prefix_offset
        assert player.source == "binary"
        assert len(player.personality) == 8

    def test_too_short(self) -> None:
        assert _try_extract_player(b"\x00" * 10, 0) is None

    def test_bad_prefix(self) -> None:
        data = b"\x01" + b"\x00" * 50
        assert _try_extract_player(data, 0) is None

    def test_name_too_short(self) -> None:
        # Name len = 1 (below _EXTRACT_MIN_NAME_LEN = 3).
        data = b"\x00" + struct.pack("<I", 1) + b"A" + b"\x00" * 50
        assert _try_extract_player(data, 0) is None

    def test_name_len_two_rejected(self) -> None:
        # Name len = 2 (below _EXTRACT_MIN_NAME_LEN = 3).
        data = b"\x00" + struct.pack("<I", 2) + b"AB" + b"\x00" * 50
        assert _try_extract_player(data, 0) is None

    def test_name_too_long(self) -> None:
        data = b"\x00" + struct.pack("<I", 100) + b"A" * 100 + b"\x00" * 50
        assert _try_extract_player(data, 0) is None

    def test_invalid_name(self) -> None:
        # Name with only digits.
        data = b"\x00" + struct.pack("<I", 5) + b"12345" + b"\x00" * 50
        assert _try_extract_player(data, 0) is None

    def test_data_too_short_after_name(self) -> None:
        name = b"John"
        # Need len >= prefix_offset+30=30 to pass first check,
        # but ne+25 > len to hit line 196. ne = 5+4 = 9, need < 34.
        # 1 prefix + 4 uint32 + 4 name + 21 padding = 30 bytes total.
        data = b"\x00" + struct.pack("<I", len(name)) + name + b"\x00" * 21
        assert len(data) == 30  # passes 30 check, but 9+25=34 > 30
        assert _try_extract_player(data, 0) is None

    def test_invalid_personality(self) -> None:
        rec = _make_player_record(
            "Test Player",
            personality=b"\xff\xff\xff\xff\xff\xff\xff\xff",
        )
        padding = b"\x00" * 10
        result = _try_extract_player(rec + padding, 0)
        assert result is not None
        player, _ = result
        assert player.personality == []

    def test_nonzero_prefix_offset(self) -> None:
        prefix = b"\xff" * 10
        rec = _make_player_record("Jane Doe")
        padding = b"\x00" * 10
        result = _try_extract_player(prefix + rec + padding, 10)
        assert result is not None
        assert result[0].uid == 10
        assert result[0].name == "Jane Doe"


class TestPass1SeparatorWalk:
    """_pass1_separator_walk tests."""

    def test_finds_records(self) -> None:
        rec = _make_player_record("John Smith")
        # Build data: 12-byte header + separator + record + padding.
        data = b"\x00" * 12 + REC_SEP + rec + b"\x00" * 30
        players: list[Player] = []
        seen: set[int] = set()
        _pass1_separator_walk(data, players, seen)
        assert len(players) >= 1
        assert players[0].name == "John Smith"

    def test_dedup_by_offset(self) -> None:
        rec = _make_player_record("John Smith")
        data = b"\x00" * 12 + REC_SEP + rec + b"\x00" * 30
        players: list[Player] = []
        expected_offset = 12 + len(REC_SEP)
        seen: set[int] = {expected_offset}
        _pass1_separator_walk(data, players, seen)
        assert len(players) == 0

    def test_invalid_record_advances(self) -> None:
        # Separator followed by non-zero prefix byte.
        data = b"\x00" * 12 + REC_SEP + b"\x01" + b"\x00" * 50
        players: list[Player] = []
        seen: set[int] = set()
        _pass1_separator_walk(data, players, seen)
        assert len(players) == 0

    def test_no_separators(self) -> None:
        data = b"\x00" * 100
        players: list[Player] = []
        seen: set[int] = set()
        _pass1_separator_walk(data, players, seen)
        assert len(players) == 0


class TestPass2RegexScan:
    """_pass2_regex_scan tests."""

    def test_finds_records(self) -> None:
        rec = _make_player_record("Anna Baker")
        data = b"\x00" * 50 + rec + b"\x00" * 30
        players: list[Player] = []
        seen: set[int] = set()
        _pass2_regex_scan(data, players, seen)
        found = [p for p in players if p.name == "Anna Baker"]
        assert len(found) >= 1

    def test_dedup_seen(self) -> None:
        rec = _make_player_record("Anna Baker")
        offset = 50
        data = b"\x00" * offset + rec + b"\x00" * 30
        players: list[Player] = []
        seen: set[int] = {offset}
        _pass2_regex_scan(data, players, seen)
        found = [p for p in players if p.name == "Anna Baker"]
        assert len(found) == 0

    def test_progress_callback(self) -> None:
        rec = _make_player_record("Test Player")
        data = b"\x00" * 50 + rec + b"\x00" * 30
        cb = MagicMock()
        players: list[Player] = []
        seen: set[int] = set()
        _pass2_regex_scan(data, players, seen, progress_cb=cb)
        # Callback should be called at i=0 (0 % 50000 == 0).
        if players:
            cb.assert_called()

    def test_no_dob_or_multiword_skipped(self) -> None:
        # Single-word name without DOB → should be skipped.
        name = b"Noname"
        rec = b"\x00" + struct.pack("<I", len(name)) + name
        # DOB with invalid year.
        rec += struct.pack("<HH", 180, 0)  # year=0 → invalid DOB
        rec += b"\x07\x03\x0b\x06\x0c"  # flags
        rec += b"\x8b\x00\x00\x00\x01\x03\x00\x00"  # nat + ref
        rec += b"\x0a\x0b\x0c\x0d\x0e\x0f\x10\x05"  # personality
        data = b"\x00" * 50 + rec + b"\x00" * 30
        players: list[Player] = []
        seen: set[int] = set()
        _pass2_regex_scan(data, players, seen)
        found = [p for p in players if p.name == "Noname"]
        assert len(found) == 0

    def test_regex_match_invalid_player(self) -> None:
        """Regex matches but _try_extract_player returns None (254→261)."""
        # Regex pattern: \x00, len_byte, \x00\x00\x00, [A-Z].
        # Name starts with 'A' (matches regex) but rest is non-printable.
        rec = b"\x00\x05\x00\x00\x00A\x01\x01\x01\x01" + b"\x00" * 30
        data = b"\xff" * 50 + rec + b"\x00" * 30
        players: list[Player] = []
        seen: set[int] = set()
        _pass2_regex_scan(data, players, seen)
        assert len(players) == 0


class TestParsePeopleDb:
    """parse_people_db integration tests with synthetic data."""

    def _make_db(self, tmp_path: Path, player_names: list[str]) -> Path:
        """Build a minimal TAD database file."""
        # 8 byte inner header + uint32 record_count.
        inner = b"\x00" * 8 + struct.pack("<I", len(player_names))
        for name in player_names:
            inner += REC_SEP
            inner += _make_player_record(name)
        inner += b"\x00" * 50  # padding
        filepath = tmp_path / "people_db.dat"
        filepath.write_bytes(_make_tad(inner))
        return filepath

    def test_parse_with_progress(self, tmp_path: Path) -> None:
        filepath = self._make_db(tmp_path, ["Alpha Beta", "Gamma Delta"])
        cb = MagicMock()
        players = parse_people_db(filepath, progress_cb=cb)
        assert len(players) >= 2
        names = {p.name for p in players}
        assert "Alpha Beta" in names
        assert "Gamma Delta" in names
        cb.assert_called()

    def test_parse_no_progress(self, tmp_path: Path) -> None:
        filepath = self._make_db(tmp_path, ["Just Name"])
        players = parse_people_db(filepath)
        assert any(p.name == "Just Name" for p in players)

    def test_empty_db(self, tmp_path: Path) -> None:
        filepath = self._make_db(tmp_path, [])
        players = parse_people_db(filepath)
        assert isinstance(players, list)


def _make_attr_block(
    *,
    vals: dict[int, int] | None = None,
) -> list[int]:
    """Build a valid 63-byte attribute block.

    Zeros at positions 20-25 and 40-42, reasonable
    non-zero values at all confirmed attribute positions.
    Overrides via *vals*.
    """
    block = [0] * 63
    # Fill confirmed positions with default non-zero values.
    defaults: dict[int, int] = {
        9: 15,
        10: 20,
        11: 17,
        12: 10,
        13: 16,
        14: 4,
        15: 14,
        16: 19,
        17: 17,
        18: 7,
        19: 20,
        26: 16,
        27: 18,
        29: 5,
        31: 19,
        32: 20,
        33: 20,
        34: 12,
        35: 20,
        36: 15,
        37: 14,
        38: 9,
        39: 4,
        43: 16,
        44: 18,
        45: 9,
        46: 13,
        47: 15,
        48: 6,
        49: 14,
        50: 9,
        51: 18,
        52: 10,
        53: 16,
        54: 7,
        55: 15,
        56: 18,
        57: 6,
        58: 12,
        59: 14,
        60: 20,
        61: 16,
        62: 13,
    }
    for pos, val in defaults.items():
        block[pos] = val
    if vals:
        for pos, val in vals.items():
            block[pos] = val
    return block


class TestIsValidAttrBlock:
    """_is_valid_attr_block tests."""

    def test_valid_block(self) -> None:
        block = bytes(_make_attr_block())
        assert _is_valid_attr_block(block) is True

    def test_value_above_20_rejected(self) -> None:
        raw = _make_attr_block()
        raw[9] = 21
        assert _is_valid_attr_block(bytes(raw)) is False

    def test_nonzero_in_zero_range_rejected(self) -> None:
        raw = _make_attr_block()
        raw[22] = 1
        assert _is_valid_attr_block(bytes(raw)) is False

    def test_nonzero_at_pos_40_rejected(self) -> None:
        raw = _make_attr_block()
        raw[40] = 1
        assert _is_valid_attr_block(bytes(raw)) is False

    def test_too_few_nonzero_rejected(self) -> None:
        block = bytes([0] * 63)
        assert _is_valid_attr_block(block) is False

    def test_exactly_min_nonzero(self) -> None:
        raw = [0] * 63
        # Fill exactly 30 positions outside zero ranges.
        keep = [
            i for i in range(63) if i not in range(20, 26) and i not in {40, 41, 42}
        ][:30]
        for pos in keep:
            raw[pos] = 10
        assert _is_valid_attr_block(bytes(raw)) is True


class TestFindAllAttrBlocks:
    """_find_all_attr_blocks tests."""

    def test_single_block_found(self) -> None:
        block = bytes(_make_attr_block())
        data = b"\xff" * 100 + block + b"\xff" * 100
        offsets, values = _find_all_attr_blocks(data)
        assert len(offsets) == 1
        assert offsets[0] == 100
        assert values[0] == list(block)

    def test_multiple_blocks(self) -> None:
        blk1 = bytes(_make_attr_block(vals={9: 15}))
        blk2 = bytes(_make_attr_block(vals={9: 18}))
        data = b"\xff" * 50 + blk1 + b"\xff" * 200 + blk2 + b"\xff" * 50
        offsets, _values = _find_all_attr_blocks(data)
        assert len(offsets) == 2
        assert offsets[0] < offsets[1]

    def test_no_blocks_in_random_data(self) -> None:
        data = bytes(range(256)) * 10
        offsets, _values = _find_all_attr_blocks(data)
        assert offsets == []

    def test_empty_data(self) -> None:
        offsets, values = _find_all_attr_blocks(b"")
        assert offsets == []
        assert values == []

    def test_block_at_start(self) -> None:
        block = bytes(_make_attr_block())
        data = block + b"\xff" * 100
        offsets, _ = _find_all_attr_blocks(data)
        assert len(offsets) == 1
        assert offsets[0] == 0

    def test_data_too_short_for_block(self) -> None:
        data = b"\x00" * 30
        offsets, _ = _find_all_attr_blocks(data)
        assert offsets == []


class TestAttrsFromBlock:
    """_attrs_from_block tests."""

    def test_extracts_confirmed_attrs(self) -> None:
        block = _make_attr_block()
        attrs = _attrs_from_block(block)
        assert attrs["Crossing"] == 15
        assert attrs["Technique"] == 20
        assert attrs["Determination"] == 20
        assert attrs["Concentration"] == 13
        assert attrs["Strength"] == 9
        assert attrs["Jumping Reach"] == 6
        assert attrs["Agility"] == 18
        assert attrs["Stamina"] == 12
        assert attrs["Pace"] == 16
        assert len(attrs) == len(ATTR_BLOCK_MAP)

    def test_zero_values_excluded(self) -> None:
        block = _make_attr_block(vals={9: 0})
        attrs = _attrs_from_block(block)
        assert "Crossing" not in attrs

    def test_all_mapped_positions_zero(self) -> None:
        block = [0] * 63
        attrs = _attrs_from_block(block)
        assert attrs == {}


class TestEnrichWithAttributes:
    """_enrich_with_attributes tests."""

    def test_block_assigned_to_nearby_player(self) -> None:
        block = bytes(_make_attr_block())
        data = b"\xff" * 100 + block + b"\xff" * 100
        player = Player(uid=200, name="Test")
        _enrich_with_attributes(data, [player])
        assert player.attributes.get("Crossing") == 15

    def test_block_too_far_away_ignored(self) -> None:
        block = bytes(_make_attr_block())
        data = b"\xff" * 10 + block + b"\xff" * 2000
        player = Player(uid=2000, name="Test")
        _enrich_with_attributes(data, [player])
        assert player.attributes == {}

    def test_no_blocks_found(self) -> None:
        data = bytes(range(256)) * 10
        player = Player(uid=100, name="Test")
        _enrich_with_attributes(data, [player])
        assert player.attributes == {}

    def test_player_before_all_blocks(self) -> None:
        block = bytes(_make_attr_block())
        data = b"\xff" * 500 + block + b"\xff" * 100
        player = Player(uid=10, name="Test")
        _enrich_with_attributes(data, [player])
        assert player.attributes == {}

    def test_progress_callback(self) -> None:
        block = bytes(_make_attr_block())
        data = b"\xff" * 100 + block + b"\xff" * 100
        player = Player(uid=200, name="Test")
        cb = MagicMock()
        _enrich_with_attributes(data, [player], progress_cb=cb)
        assert cb.call_count >= 2

    def test_multiple_players_multiple_blocks(self) -> None:
        blk1 = bytes(_make_attr_block(vals={9: 12}))
        blk2 = bytes(_make_attr_block(vals={9: 18}))
        gap = b"\xff" * 200
        data = gap + blk1 + gap + gap + blk2 + gap
        off1 = 200
        off2 = 200 + 63 + 200 + 200
        p1 = Player(uid=off1 + 63 + 50, name="Player1")
        p2 = Player(uid=off2 + 63 + 50, name="Player2")
        _enrich_with_attributes(data, [p1, p2])
        assert p1.attributes.get("Crossing") == 12
        assert p2.attributes.get("Crossing") == 18


class TestSearchPlayers:
    """search_players tests."""

    def test_match(self) -> None:
        players = [Player(name="John Smith"), Player(name="Jane Doe")]
        result = search_players(players, "john")
        assert len(result) == 1
        assert result[0].name == "John Smith"

    def test_no_match(self) -> None:
        players = [Player(name="John Smith")]
        assert search_players(players, "xyz") == []

    def test_case_insensitive(self) -> None:
        players = [Player(name="John Smith")]
        assert len(search_players(players, "JOHN")) == 1

    def test_partial_match(self) -> None:
        players = [Player(name="Jonathan")]
        assert len(search_players(players, "jona")) == 1
