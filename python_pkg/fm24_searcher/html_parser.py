"""HTML import parser for FM24 exported views.

FM24 allows exporting search/scout views via Ctrl+P (Printing).
The result is an HTML file containing player data in tables.
This module parses that HTML to extract player attributes.

Supported: the default FM24 HTML export format with
<table> containing player rows and attribute columns.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
import html
import re
from typing import TYPE_CHECKING

from python_pkg.fm24_searcher.models import ALL_VISIBLE_ATTRS, GOALKEEPER_ATTRS, Player

if TYPE_CHECKING:
    from pathlib import Path

# Common FM attribute header normalizations.
_HEADER_MAP: dict[str, str] = {
    "cor": "Corners",
    "cro": "Crossing",
    "dri": "Dribbling",
    "fin": "Finishing",
    "fir": "First Touch",
    "fre": "Free Kick",
    "hea": "Heading",
    "lon": "Long Shots",
    "l th": "Long Throws",
    "mar": "Marking",
    "pas": "Passing",
    "pen": "Penalty Taking",
    "tck": "Tackling",
    "tec": "Technique",
    "agg": "Aggression",
    "ant": "Anticipation",
    "bra": "Bravery",
    "cmp": "Composure",
    "cnt": "Concentration",
    "dec": "Decisions",
    "det": "Determination",
    "fla": "Flair",
    "ldr": "Leadership",
    "otb": "Off The Ball",
    "pos": "Positioning",
    "tea": "Teamwork",
    "vis": "Vision",
    "wor": "Work Rate",
    "acc": "Acceleration",
    "agi": "Agility",
    "bal": "Balance",
    "jum": "Jumping Reach",
    "nat": "Natural Fitness",
    "pac": "Pace",
    "sta": "Stamina",
    "str": "Strength",
    # Goalkeeper
    "aer": "Aerial Reach",
    "cmd": "Command of Area",
    "com": "Communication",
    "ecc": "Eccentricity",
    "han": "Handling",
    "kic": "Kicking",
    "1v1": "One on Ones",
    "pun": "Punching (Tendency)",
    "ref": "Reflexes",
    "rus": "Rushing Out (Tendency)",
    "thr": "Throwing",
    # Alternative spellings
    "wk r": "Work Rate",
    "work rate": "Work Rate",
    "corners": "Corners",
    "crossing": "Crossing",
    "dribbling": "Dribbling",
    "finishing": "Finishing",
    "first touch": "First Touch",
    "heading": "Heading",
    "long shots": "Long Shots",
    "long throws": "Long Throws",
    "marking": "Marking",
    "passing": "Passing",
    "tackling": "Tackling",
    "technique": "Technique",
}

# Build reverse lookup: normalized attr name → canonical.
_ALL_ATTRS_LOWER = {a.lower(): a for a in ALL_VISIBLE_ATTRS + GOALKEEPER_ATTRS}

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _strip_html(text: str) -> str:
    """Remove HTML tags and decode entities."""
    text = _TAG_RE.sub("", text)
    text = html.unescape(text)
    return _WS_RE.sub(" ", text).strip()


def _normalize_header(raw: str) -> str | None:
    """Map an HTML column header to a canonical attribute name."""
    clean = _strip_html(raw).strip().lower()
    # Direct lookup.
    if clean in _HEADER_MAP:
        return _HEADER_MAP[clean]
    if clean in _ALL_ATTRS_LOWER:
        return _ALL_ATTRS_LOWER[clean]
    # Truncated header: try first 3 chars.
    short = clean[:3]
    if short in _HEADER_MAP:
        return _HEADER_MAP[short]
    return None


def _extract_tables(html_content: str) -> list[list[list[str]]]:
    """Parse HTML tables into a list of row lists.

    Each row is a list of cell strings. Returns list of tables.
    """
    tables: list[list[list[str]]] = []
    table_re = re.compile(
        r"<table[^>]*>(.*?)</table>",
        re.DOTALL | re.IGNORECASE,
    )
    row_re = re.compile(
        r"<tr[^>]*>(.*?)</tr>",
        re.DOTALL | re.IGNORECASE,
    )
    cell_re = re.compile(
        r"<t[hd][^>]*>(.*?)</t[hd]>",
        re.DOTALL | re.IGNORECASE,
    )

    for table_match in table_re.finditer(html_content):
        rows: list[list[str]] = []
        for row_match in row_re.finditer(table_match.group(1)):
            cells = [
                _strip_html(c.group(1)) for c in cell_re.finditer(row_match.group(1))
            ]
            if cells:
                rows.append(cells)
        if rows:
            tables.append(rows)
    return tables


_MIN_TABLE_ROWS = 2
_MIN_ATTR_VAL = 1
_MAX_ATTR_VAL = 20

# Map from lowercase header text to _ColMap field name.
_HDR_FIELD: dict[str, str] = {
    "name": "name",
    "player": "name",
    "club": "club",
    "team": "club",
    "nat": "nat",
    "nationality": "nat",
    "position": "pos",
    "pos": "pos",
    "ca": "ca",
    "ability": "ca",
    "pa": "pa",
    "potential": "pa",
    "value": "value",
    "val": "value",
    "wage": "wage",
}

# Map from _ColMap field name to Player attribute name.
_FIELD_ATTR: list[tuple[str, str]] = [
    ("club", "club"),
    ("nat", "nationality"),
    ("pos", "position"),
    ("value", "value"),
    ("wage", "wage"),
]


@dataclass
class _ColMap:
    """Column index mapping from parsed HTML table headers."""

    name: int | None = None
    club: int | None = None
    nat: int | None = None
    pos: int | None = None
    ca: int | None = None
    pa: int | None = None
    value: int | None = None
    wage: int | None = None
    attrs: dict[int, str] = field(default_factory=dict)


def _build_col_map(headers: list[str]) -> _ColMap:
    """Build column index mapping from table header cells."""
    cols = _ColMap()
    for i, hdr in enumerate(headers):
        h = hdr.strip().lower()
        if field := _HDR_FIELD.get(h):
            setattr(cols, field, i)
        elif attr_name := _normalize_header(hdr):
            cols.attrs[i] = attr_name
    return cols


def _apply_attr(player: Player, attr_name: str, val_str: str) -> None:
    """Parse val_str and set an attribute on player if value is in range."""
    if "-" in val_str and val_str[0].isdigit():
        val_str = val_str.split("-", maxsplit=1)[0]
    with contextlib.suppress(ValueError):
        val = int(val_str)
        if _MIN_ATTR_VAL <= val <= _MAX_ATTR_VAL:
            if attr_name in ALL_VISIBLE_ATTRS:
                player.attributes[attr_name] = val
            else:
                player.gk_attributes[attr_name] = val


def _parse_player_row(row: list[str], cols: _ColMap) -> Player | None:
    """Parse one data row into a Player; returns None if row is invalid."""
    if cols.name is None or len(row) <= cols.name:
        return None
    name = row[cols.name].strip()
    if not name:
        return None
    player = Player(name=name, source="html")

    def _get(col: int | None) -> str | None:
        return row[col].strip() if col is not None and col < len(row) else None

    for col_field, attr in _FIELD_ATTR:
        if val := _get(getattr(cols, col_field)):
            setattr(player, attr, val)
    with contextlib.suppress(ValueError, TypeError):
        if raw := _get(cols.ca):
            player.current_ability = int(raw)
    with contextlib.suppress(ValueError, TypeError):
        if raw := _get(cols.pa):
            player.potential_ability = int(raw)
    for col_idx, attr_name in cols.attrs.items():
        if col_idx < len(row):
            _apply_attr(player, attr_name, row[col_idx].strip())
    return player


def parse_html_export(filepath: Path) -> list[Player]:
    """Parse an FM24 HTML export file into Player objects.

    Looks for tables where column headers map to known FM
    attributes. The 'Name' column is required.
    """
    content = filepath.read_text(encoding="utf-8", errors="replace")
    all_players: list[Player] = []
    for table in _extract_tables(content):
        if len(table) < _MIN_TABLE_ROWS:
            continue
        cols = _build_col_map(table[0])
        if cols.name is None:
            continue
        for row in table[1:]:
            player = _parse_player_row(row, cols)
            if player is not None:
                all_players.append(player)
    return all_players


def merge_players(
    binary_players: list[Player],
    html_players: list[Player],
) -> list[Player]:
    """Merge binary-parsed data with HTML-imported attributes.

    Matches by name (case-insensitive). Binary provides
    DOB/CA/personality; HTML provides visible attributes.
    """
    html_by_name: dict[str, Player] = {}
    for p in html_players:
        html_by_name[p.name.lower()] = p

    merged: list[Player] = []
    matched_names: set[str] = set()

    for bp in binary_players:
        key = bp.name.lower()
        if key in html_by_name:
            hp = html_by_name[key]
            bp.attributes = hp.attributes
            bp.gk_attributes = hp.gk_attributes
            bp.club = hp.club or bp.club
            bp.nationality = hp.nationality or bp.nationality
            bp.position = hp.position or bp.position
            bp.value = hp.value or bp.value
            bp.wage = hp.wage or bp.wage
            if hp.current_ability > 0:
                bp.current_ability = hp.current_ability
            if hp.potential_ability > 0:
                bp.potential_ability = hp.potential_ability
            bp.source = "merged"
            matched_names.add(key)
        merged.append(bp)

    # Add HTML-only players not matched.
    merged.extend(hp for hp in html_players if hp.name.lower() not in matched_names)

    return merged
