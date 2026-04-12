"""CLI dump mode for FM24 Database Searcher.

Outputs player data as plain text so LLMs can inspect
and verify extracted values.

Usage::

    python -m python_pkg.fm24_searcher --dump
    python -m python_pkg.fm24_searcher --dump --search Messi
    python -m python_pkg.fm24_searcher --dump --limit 20
    python -m python_pkg.fm24_searcher --dump --attrs
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import TYPE_CHECKING

from python_pkg.fm24_searcher.binary_parser import (
    parse_people_db,
    search_players,
)
from python_pkg.fm24_searcher.models import ALL_VISIBLE_ATTRS, Player

if TYPE_CHECKING:
    from collections.abc import Sequence

# Default path to FM24 people database.
_DEFAULT_DB = (
    Path.home()
    / ".local/share/Steam/steamapps/common"
    / "Football Manager 2024/data/database/db"
    / "2400/2400_fm/people_db.dat"
)

_DEFAULT_LIMIT = 50


def _format_player_attrs(player: Player) -> list[str]:
    """Format the attributes section for a player."""
    if not player.attributes:
        return ["  (no attribute block found)"]
    lines = ["  Attributes:"]
    lines += [
        f"    {attr}: {val}"
        for attr in ALL_VISIBLE_ATTRS
        if (val := player.attributes.get(attr, 0)) > 0
    ]
    missing = [a for a in ALL_VISIBLE_ATTRS if a not in player.attributes]
    if missing:
        lines.append(f"  Missing attrs: {', '.join(missing)}")
    return lines


_OPTIONAL_FIELDS = [
    ("DOB", "date_of_birth"),
    ("CA", "current_ability"),
    ("PA", "potential_ability"),
    ("Nationality", "nationality"),
    ("Club", "club"),
    ("Position", "position"),
    ("Personality bytes", "personality"),
]


def _format_player(player: Player, *, show_attrs: bool = False) -> str:
    """Format one player as a multi-line text block."""
    lines = [f"=== {player.name} ==="]
    lines += [
        f"  {label}: {getattr(player, field)}"
        for label, field in _OPTIONAL_FIELDS
        if getattr(player, field)
    ]
    if show_attrs:
        lines.extend(_format_player_attrs(player))
    lines.append(f"  Source: {player.source}")
    lines.append(f"  UID (byte offset): {player.uid}")
    return "\n".join(lines)


def _format_tsv_header(*, show_attrs: bool) -> str:
    """Build TSV header line."""
    cols = ["Name", "DOB", "CA", "PA", "Personality", "UID"]
    if show_attrs:
        cols.extend(ALL_VISIBLE_ATTRS)
    return "\t".join(cols)


def _format_tsv_row(player: Player, *, show_attrs: bool) -> str:
    """Format one player as a TSV row."""
    cols = [
        player.name,
        player.date_of_birth,
        str(player.current_ability) if player.current_ability else "",
        str(player.potential_ability) if player.potential_ability else "",
        ",".join(str(p) for p in player.personality),
        str(player.uid),
    ]
    if show_attrs:
        for attr in ALL_VISIBLE_ATTRS:
            val = player.attributes.get(attr, 0)
            cols.append(str(val) if val > 0 else "")
    return "\t".join(cols)


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for CLI mode."""
    parser = argparse.ArgumentParser(
        prog="fm24_searcher",
        description="FM24 Database Searcher — CLI dump mode",
    )
    parser.add_argument(
        "--dump",
        action="store_true",
        help="Enable CLI dump mode (text output, no GUI)",
    )
    parser.add_argument(
        "--search",
        type=str,
        default="",
        help="Filter players by name substring",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=_DEFAULT_LIMIT,
        help=f"Max number of players to show (default {_DEFAULT_LIMIT})",
    )
    parser.add_argument(
        "--attrs",
        action="store_true",
        help="Include all visible attributes in output",
    )
    parser.add_argument(
        "--tsv",
        action="store_true",
        help="Output as tab-separated values (machine-readable)",
    )
    parser.add_argument(
        "--db",
        type=str,
        default="",
        help="Path to people_db.dat (overrides default)",
    )
    parser.add_argument(
        "--with-attrs-only",
        action="store_true",
        help="Only show players that have attribute blocks",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show summary statistics about the loaded database",
    )
    return parser


def _print_stats(players: list[Player]) -> None:
    """Print summary statistics about loaded players."""
    total = len(players)
    with_dob = sum(1 for p in players if p.date_of_birth)
    with_attrs = sum(1 for p in players if p.attributes)
    with_ca = sum(1 for p in players if p.current_ability)
    sys.stdout.write(f"Total players: {total}\n")
    sys.stdout.write(f"With DOB: {with_dob}\n")
    sys.stdout.write(f"With attributes: {with_attrs}\n")
    sys.stdout.write(f"With CA/PA: {with_ca}\n")
    if with_attrs > 0:
        avg_attrs = sum(len(p.attributes) for p in players) / with_attrs
        sys.stdout.write(f"Avg attributes per player: {avg_attrs:.1f}\n")
    if total == 0:
        return
    # Attribute coverage
    attr_counts: dict[str, int] = {}
    for p in players:
        for attr in p.attributes:
            attr_counts[attr] = attr_counts.get(attr, 0) + 1
    if attr_counts:
        sys.stdout.write("Attribute coverage:\n")
        for attr in ALL_VISIBLE_ATTRS:
            count = attr_counts.get(attr, 0)
            pct = 100 * count / with_attrs if with_attrs else 0
            bar = "*" * int(pct / 5)
            sys.stdout.write(
                f"  {attr:20s} {count:4d}/{with_attrs:4d} ({pct:5.1f}%) {bar}\n"
            )


def run_dump(argv: Sequence[str] | None = None) -> int:
    """Execute CLI dump mode. Returns exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.dump:
        return 1

    db_path = Path(args.db) if args.db else _DEFAULT_DB
    if not db_path.exists():
        return 2

    def progress(msg: str, pct: int) -> None:
        sys.stderr.write(f"\r{msg} {pct}%")
        sys.stderr.flush()

    players = parse_people_db(db_path, progress_cb=progress)
    sys.stderr.write("\n")

    if args.search:
        players = search_players(players, args.search)

    if args.with_attrs_only:
        players = [p for p in players if p.attributes]

    if args.stats:
        _print_stats(players)
        return 0

    # Apply limit
    limited = players[: args.limit]
    total = len(players)
    shown = len(limited)

    # Output
    if args.tsv:
        sys.stdout.write(_format_tsv_header(show_attrs=args.attrs) + "\n")
        for p in limited:
            sys.stdout.write(_format_tsv_row(p, show_attrs=args.attrs) + "\n")
    else:
        for p in limited:
            sys.stdout.write(_format_player(p, show_attrs=args.attrs) + "\n\n")

    sys.stdout.write(f"Showing {shown} of {total} players\n")
    return 0
