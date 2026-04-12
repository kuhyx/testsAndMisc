r"""Binary parser for FM24 database files.

Extracts player names, DOB, personality bytes from
people_db.dat and save game files.  CA/PA require HTML
import; the binary DB does not expose current/potential
ability as readable values.  Nationality is stored as a
uint32 at +13 after the name end, not a uint16 at +9.

File format summary:
- Outer wrapper: 8-byte magic + zstd compressed payload
- Magic: \\x03\\x01tad.\\xef\\r
- Payload: 8-byte inner header + uint32 record_count + records
- Multi-frame files (client_db, server_db, saves): \\x02\\x01fmf.
  container with multiple zstd frames
"""

from __future__ import annotations

import bisect
import datetime
import re
import struct
from typing import TYPE_CHECKING

import numpy as np
import zstandard

from python_pkg.fm24_searcher.models import Player

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

TAD_MAGIC = b"\x03\x01tad.\xef\r"
FMF_MAGIC = b"\x02\x01fmf."
ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"

# Record separator found between simple records.
REC_SEP = b"\x05\x00\x00\x00\x00"

MAX_OUTPUT = 500 * 1024 * 1024  # 500 MB decompression limit

# DOB validation bounds.
_MIN_YEAR = 1930
_MAX_YEAR = 2012
_MAX_DAY_OF_YEAR = 366

# Name length bounds.
_BOUNDARY_MIN_NAME_LEN = 3
_EXTRACT_MIN_NAME_LEN = 3
_MAX_NAME_LEN = 80

# Attribute bounds.
_MAX_PERSONALITY_VAL = 20

# --- Attribute block constants ---
_ATTR_BLOCK_SIZE = 63
_ATTR_ZERO_RANGE = range(20, 26)
_ATTR_ZERO_SINGLES = frozenset({40, 41, 42})
_ATTR_MIN_NONZERO = 30
_ATTR_SEARCH_WINDOW = 1500
_SIX_ZEROS = b"\x00\x00\x00\x00\x00\x00"

# Byte position → attribute name (36 confirmed visible attributes).
ATTR_BLOCK_MAP: dict[int, str] = {
    9: "Crossing",
    10: "Technique",
    11: "Balance",
    12: "Heading",
    13: "Free Kick",
    14: "Marking",
    15: "Off The Ball",
    16: "Vision",
    17: "Decisions",
    18: "Tackling",
    19: "Flair",
    26: "Finishing",
    27: "First Touch",
    29: "Positioning",
    31: "Dribbling",
    32: "Passing",
    36: "Corners",
    37: "Leadership",
    38: "Work Rate",
    39: "Long Throws",
    43: "Anticipation",
    45: "Strength",
    46: "Teamwork",
    47: "Penalty Taking",
    48: "Jumping Reach",
    49: "Long Shots",
    51: "Agility",
    52: "Bravery",
    53: "Composure",
    54: "Aggression",
    55: "Acceleration",
    58: "Stamina",
    59: "Natural Fitness",
    60: "Determination",
    61: "Pace",
    62: "Concentration",
}


def _is_valid_attr_block(block: bytes) -> bool:
    """Check whether *block* (63 bytes) matches the attribute pattern."""
    if any(b > _MAX_PERSONALITY_VAL for b in block):
        return False
    if any(block[j] != 0 for j in _ATTR_ZERO_RANGE):
        return False
    if any(block[j] != 0 for j in _ATTR_ZERO_SINGLES):
        return False
    return sum(1 for b in block if b > 0) >= _ATTR_MIN_NONZERO


def _find_all_attr_blocks(data: bytes) -> tuple[list[int], list[list[int]]]:
    """Locate every 63-byte attribute block in *data*.

    Phase 1: collect all candidate block starts at C speed
    using ``bytes.find`` on the six-zero anchor at positions
    20-25.  Phase 2: validate all candidates at once with
    numpy vectorised operations.

    Returns ``(offsets, values)`` where both lists are sorted
    by offset and have the same length.
    """
    # Phase 1: C-speed scan for the six-zero anchor.
    candidates: list[int] = []
    pos = 0
    data_len = len(data)
    while True:
        idx = data.find(_SIX_ZEROS, pos)
        if idx < 0:
            break
        block_start = idx - 20
        if block_start >= 0 and block_start + _ATTR_BLOCK_SIZE <= data_len:
            candidates.append(block_start)
        pos = idx + 1
    if not candidates:
        return [], []

    # Phase 2: bulk numpy validation of all candidate blocks.
    arr = np.frombuffer(data, dtype=np.uint8)
    bs = np.array(candidates, dtype=np.int32)
    # sliding_window_view creates a zero-copy view; shape (N-62, 63).
    windows = np.lib.stride_tricks.sliding_window_view(arr, _ATTR_BLOCK_SIZE)
    # Guard: discard any index beyond the last valid window.
    valid_idx = bs[bs < len(windows)]
    blocks = windows[valid_idx]  # copies only the selected rows

    # All bytes must be <= _MAX_PERSONALITY_VAL (20).
    cond1 = (blocks <= _MAX_PERSONALITY_VAL).all(axis=1)
    # Positions 40-42 must be zero (positions 20-25 are
    # guaranteed zero by the six-zero anchor construction).
    cond3 = (blocks[:, [40, 41, 42]] == 0).all(axis=1)
    # At least _ATTR_MIN_NONZERO (30) bytes must be non-zero.
    cond4 = (blocks > 0).sum(axis=1) >= _ATTR_MIN_NONZERO

    valid_mask = cond1 & cond3 & cond4
    offsets: list[int] = [int(x) for x in valid_idx[valid_mask]]
    values: list[list[int]] = [[int(b) for b in row] for row in blocks[valid_mask]]
    return offsets, values


def _attrs_from_block(block: list[int]) -> dict[str, int]:
    """Map a raw 63-byte block to ``{attr_name: value}``."""
    return {name: block[pos] for pos, name in ATTR_BLOCK_MAP.items() if block[pos] > 0}


def _enrich_with_attributes(
    data: bytes,
    players: list[Player],
    progress_cb: Callable[[str, int], None] | None = None,
) -> None:
    """Find attribute blocks and assign them to nearby players.

    Each player's ``uid`` is its prefix-byte offset in *data*.
    The nearest valid block within *_ATTR_SEARCH_WINDOW* bytes
    before that offset is picked.
    """
    if progress_cb:
        progress_cb("Indexing attribute blocks...", 96)
    block_offsets, block_values = _find_all_attr_blocks(data)
    if not block_offsets:
        return

    if progress_cb:
        progress_cb(
            f"Assigning attributes ({len(block_offsets)} blocks)...",
            97,
        )
    for player in players:
        idx = bisect.bisect_right(block_offsets, player.uid) - 1
        if idx < 0:
            continue
        if player.uid - block_offsets[idx] > _ATTR_SEARCH_WINDOW:
            continue
        player.attributes = _attrs_from_block(block_values[idx])


def _decompress_single(raw: bytes) -> bytes:
    """Decompress a TAD-magic .dat file (single zstd frame)."""
    if raw[:8] != TAD_MAGIC:
        msg = f"Expected TAD magic, got {raw[:8]!r}"
        raise ValueError(msg)
    dctx = zstandard.ZstdDecompressor()
    result: bytes = dctx.decompress(raw[8:], max_output_size=MAX_OUTPUT)
    return result


def _decompress_multiframe(raw: bytes) -> list[bytes]:
    """Decompress a multi-frame FMF container.

    Returns list of decompressed frame payloads.
    """
    dctx = zstandard.ZstdDecompressor()
    frames: list[bytes] = []
    idx = 0
    while True:
        pos = raw.find(ZSTD_MAGIC, idx)
        if pos < 0:
            break
        try:
            data = dctx.decompress(
                raw[pos:],
                max_output_size=MAX_OUTPUT,
            )
            frames.append(data)
        except zstandard.ZstdError:
            pass
        idx = pos + 4
    return frames


def decompress_file(filepath: Path) -> bytes | list[bytes]:
    """Auto-detect format and decompress.

    Single frame → bytes, multi-frame → list[bytes].
    """
    raw = filepath.read_bytes()
    if raw[:8] == TAD_MAGIC:
        return _decompress_single(raw)
    if FMF_MAGIC in raw[:20]:
        return _decompress_multiframe(raw)
    msg = f"Unknown file format: {filepath}"
    raise ValueError(msg)


def _dob_from_bytes(data: bytes, offset: int) -> str:
    """Extract DOB as ISO string from 4 bytes.

    Format: uint16 day-of-year + uint16 year.
    """
    day_of_year = struct.unpack_from("<H", data, offset)[0]
    year = struct.unpack_from("<H", data, offset + 2)[0]
    if not (_MIN_YEAR <= year <= _MAX_YEAR and 1 <= day_of_year <= _MAX_DAY_OF_YEAR):
        return ""
    try:
        dt = datetime.date(year, 1, 1) + datetime.timedelta(
            days=day_of_year - 1,
        )
        return dt.isoformat()
    except (ValueError, OverflowError):
        return ""


def _find_name_boundaries(
    data: bytes,
    name_pos: int,
) -> tuple[str, int, int] | None:
    """Find name boundaries from a position in the data.

    Given a name fragment position, find the uint32 length
    prefix and return (full_name, start_offset, end_offset).
    """
    for back in range(_MAX_NAME_LEN):
        off = name_pos - back - 4
        if off < 0:
            continue
        name_len = struct.unpack_from("<I", data, off)[0]
        if not (_BOUNDARY_MIN_NAME_LEN <= name_len <= _MAX_NAME_LEN):
            continue
        ns = off + 4
        ne = ns + name_len
        if ns <= name_pos < ne:
            candidate = data[ns:ne]
            try:
                name = candidate.decode("utf-8")
                if name.isprintable():
                    return (name, off, ne)
            except UnicodeDecodeError:
                continue
    return None


def _is_valid_name(data: bytes, offset: int, length: int) -> str:
    """Try to decode a name at offset with given length.

    Returns the name string if valid, empty string otherwise.
    """
    end = offset + length
    if end > len(data):
        return ""
    candidate = data[offset:end]
    try:
        name = candidate.decode("utf-8")
    except UnicodeDecodeError:
        return ""
    # First and last chars must be alphabetic; names do not
    # start or end with punctuation or symbols like '<'.
    if not (name[0].isalpha() and name[-1].isalpha()):
        return ""
    if not all(c.isprintable() or c in " -'." for c in name):
        return ""
    return name


def _try_extract_player(
    data: bytes,
    prefix_offset: int,
) -> tuple[Player, int] | None:
    """Try to extract a player record starting at prefix_offset.

    Returns (Player, name_end_offset) or None if not a valid
    record.
    """
    if prefix_offset + 30 > len(data):
        return None
    # Prefix byte should be 0x00.
    if data[prefix_offset] != 0x00:
        return None
    name_len = struct.unpack_from(
        "<I",
        data,
        prefix_offset + 1,
    )[0]
    if not (_EXTRACT_MIN_NAME_LEN <= name_len <= _MAX_NAME_LEN):
        return None
    name_start = prefix_offset + 5
    name = _is_valid_name(data, name_start, name_len)
    if not name:
        return None
    ne = name_start + name_len
    if ne + 25 > len(data):
        return None

    dob = _dob_from_bytes(data, ne)

    # 8 personality bytes at +17 from name end.
    personality = list(data[ne + 17 : ne + 25])
    valid_pers = all(0 <= p <= _MAX_PERSONALITY_VAL for p in personality)

    player = Player(
        uid=prefix_offset,
        name=name,
        date_of_birth=dob,
        personality=personality if valid_pers else [],
        source="binary",
    )
    return (player, ne)


def _pass1_separator_walk(
    data: bytes,
    players: list[Player],
    seen_offsets: set[int],
) -> None:
    """Walk separator-delimited records (short/retired players)."""
    idx = 12
    while True:
        pos = data.find(REC_SEP, idx)
        if pos < 0:
            break
        prefix_off = pos + 5
        result = _try_extract_player(data, prefix_off)
        if result:
            player, ne = result
            if prefix_off not in seen_offsets:
                seen_offsets.add(prefix_off)
                players.append(player)
            idx = ne
        else:
            idx = pos + 1


def _pass2_regex_scan(
    data: bytes,
    players: list[Player],
    seen_offsets: set[int],
    progress_cb: Callable[[str, int], None] | None = None,
) -> None:
    """Scan for name patterns to find active player records."""
    pattern = re.compile(
        b"\\x00[\\x02-\\x50]\\x00\\x00\\x00[A-Z\\xc0-\\xff]",
    )
    matches = list(pattern.finditer(data))
    total_matches = len(matches)
    for i, m in enumerate(matches):
        prefix_off = m.start()
        if prefix_off in seen_offsets:
            continue
        result = _try_extract_player(data, prefix_off)
        if result:
            player, _ne = result
            has_dob = bool(player.date_of_birth)
            has_multiword = " " in player.name
            if (has_dob or has_multiword) and prefix_off not in seen_offsets:
                seen_offsets.add(prefix_off)
                players.append(player)
        if progress_cb and i % 50000 == 0 and total_matches > 0:
            pct = 30 + int(65 * i / total_matches)
            progress_cb(
                f"Scanning... {len(players)} players found",
                pct,
            )


def parse_people_db(
    filepath: Path,
    progress_cb: Callable[[str, int], None] | None = None,
) -> list[Player]:
    """Parse people_db.dat and extract player records.

    Args:
        filepath: Path to people_db.dat.
        progress_cb: Optional callback(stage_msg, percent).

    Uses a two-pass approach:
    1. Walk separator-delimited records (short/retired).
    2. Scan for name patterns to find active player records.
    """
    if progress_cb:
        progress_cb("Decompressing database...", 0)
    data = _decompress_single(filepath.read_bytes())
    if progress_cb:
        progress_cb("Decompressed, scanning records...", 15)
    struct.unpack_from("<I", data, 8)[0]

    players: list[Player] = []
    seen_offsets: set[int] = set()

    _pass1_separator_walk(data, players, seen_offsets)

    if progress_cb:
        progress_cb(
            f"Pass 1 done ({len(players)} found), scanning full database...",
            30,
        )

    _pass2_regex_scan(data, players, seen_offsets, progress_cb)

    _enrich_with_attributes(data, players, progress_cb)

    if progress_cb:
        progress_cb(
            f"Done — {len(players)} players loaded",
            100,
        )
    return players


def search_players(
    players: list[Player],
    query: str,
) -> list[Player]:
    """Simple name-based search."""
    query_lower = query.lower()
    return [p for p in players if query_lower in p.name.lower()]
