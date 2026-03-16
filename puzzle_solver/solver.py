"""BFS puzzle solver for sliding-square puzzles.

The player slides in one of 4 directions until hitting a square (or dies
if no square is reached).  Special square types modify traversal:
  - PORTAL:     pass-through when approached from the marked side
  - TELEPORTER: warp to paired teleporter on landing
  - KEY:        removes the matching LOCK square from the board
  - LOCK:       solid until its KEY is collected, then disappears
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path
from typing import Any

# ── Direction helpers ────────────────────────────────────────────────
UP = (-1, 0)
DOWN = (1, 0)
LEFT = (0, -1)
RIGHT = (0, 1)

DIRECTIONS: dict[str, tuple[int, int]] = {
    "up": UP,
    "down": DOWN,
    "left": LEFT,
    "right": RIGHT,
}

# When moving in a direction, which side of the target square do we approach?
DIR_TO_APPROACH_SIDE: dict[tuple[int, int], str] = {
    RIGHT: "left",
    LEFT: "right",
    DOWN: "up",
    UP: "down",
}


# ── Data model ───────────────────────────────────────────────────────
class SquareType(Enum):
    """Types of squares in the puzzle grid."""

    NORMAL = "normal"
    PLAYER = "player"
    GOAL = "goal"
    PORTAL = "portal"
    TELEPORTER = "teleporter"
    KEY = "key"
    LOCK = "lock"


@dataclass(frozen=True)
class Square:
    """A single square on the puzzle board."""

    pos: tuple[int, int]
    square_type: SquareType
    portal_side: str | None = None  # PORTAL: side with inner square
    teleporter_group: int | None = None  # TELEPORTER: pair id
    lock_id: int | None = None  # KEY / LOCK: matching id


@dataclass(frozen=True)
class State:
    """Immutable snapshot of player position and remaining locks."""

    pos: tuple[int, int]
    active_locks: frozenset[tuple[int, int]]


@dataclass
class _ParseMetadata:
    """Intermediate bookkeeping collected while parsing squares."""

    player_start: tuple[int, int]
    goal_pos: tuple[int, int]
    teleporter_groups: dict[int, list[tuple[int, int]]]
    key_map: dict[int, tuple[int, int]]
    lock_map: dict[int, tuple[int, int]]


def _parse_square_list(
    square_dicts: list[dict[str, Any]],
) -> tuple[dict[tuple[int, int], Square], _ParseMetadata]:
    """Parse the JSON squares list into Square objects and metadata."""
    squares: dict[tuple[int, int], Square] = {}
    player_start: tuple[int, int] | None = None
    goal_pos: tuple[int, int] | None = None
    teleporter_groups: dict[int, list[tuple[int, int]]] = {}
    key_map: dict[int, tuple[int, int]] = {}
    lock_map: dict[int, tuple[int, int]] = {}

    for sd in square_dicts:
        pos = (int(sd["pos"][0]), int(sd["pos"][1]))
        sq_type = SquareType(sd["type"])
        sq = Square(
            pos=pos,
            square_type=sq_type,
            portal_side=sd.get("side"),
            teleporter_group=sd.get("group"),
            lock_id=sd.get("lock_id"),
        )
        squares[pos] = sq

        if sq_type == SquareType.PLAYER:
            player_start = pos
        elif sq_type == SquareType.GOAL:
            goal_pos = pos
        elif sq_type == SquareType.TELEPORTER and sq.teleporter_group is not None:
            teleporter_groups.setdefault(sq.teleporter_group, []).append(pos)
        elif sq_type == SquareType.KEY and sq.lock_id is not None:
            key_map[sq.lock_id] = pos
        elif sq_type == SquareType.LOCK and sq.lock_id is not None:
            lock_map[sq.lock_id] = pos

    if player_start is None:
        msg = "No player start position found in puzzle data"
        raise ValueError(msg)
    if goal_pos is None:
        msg = "No goal position found in puzzle data"
        raise ValueError(msg)

    metadata = _ParseMetadata(
        player_start, goal_pos, teleporter_groups, key_map, lock_map
    )
    return squares, metadata


def _pair_teleporters(
    groups: dict[int, list[tuple[int, int]]],
) -> dict[tuple[int, int], tuple[int, int]]:
    """Pair up teleporter squares by group id."""
    pairs: dict[tuple[int, int], tuple[int, int]] = {}
    expected_pair_size = 2
    for gid, positions in groups.items():
        if len(positions) != expected_pair_size:
            msg = f"Teleporter group {gid} has {len(positions)} members (need 2)"
            raise ValueError(msg)
        pairs[positions[0]] = positions[1]
        pairs[positions[1]] = positions[0]
    return pairs


def _map_keys_to_locks(
    key_map: dict[int, tuple[int, int]],
    lock_map: dict[int, tuple[int, int]],
) -> dict[tuple[int, int], tuple[int, int]]:
    """Map each key position to its corresponding lock position."""
    key_to_lock: dict[tuple[int, int], tuple[int, int]] = {}
    for lid, kpos in key_map.items():
        if lid not in lock_map:
            msg = f"Key with lock_id={lid} has no matching lock"
            raise ValueError(msg)
        key_to_lock[kpos] = lock_map[lid]
    return key_to_lock


@dataclass
class Puzzle:
    """Full puzzle definition with squares, teleporters, and key-lock pairs."""

    squares: dict[tuple[int, int], Square]
    player_start: tuple[int, int]
    goal_pos: tuple[int, int]
    teleporter_pairs: dict[tuple[int, int], tuple[int, int]]
    key_to_lock: dict[tuple[int, int], tuple[int, int]]
    grid_bounds: tuple[int, int, int, int]  # min_r, max_r, min_c, max_c

    # ── JSON round-trip ──────────────────────────────────────────────
    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Puzzle:
        """Build a Puzzle from a parsed JSON dict."""
        squares, metadata = _parse_square_list(data["squares"])
        teleporter_pairs = _pair_teleporters(metadata.teleporter_groups)
        key_to_lock = _map_keys_to_locks(metadata.key_map, metadata.lock_map)

        all_pos = list(squares)
        rows = [p[0] for p in all_pos]
        cols = [p[1] for p in all_pos]
        bounds = (min(rows) - 1, max(rows) + 1, min(cols) - 1, max(cols) + 1)

        return cls(
            squares,
            metadata.player_start,
            metadata.goal_pos,
            teleporter_pairs,
            key_to_lock,
            bounds,
        )

    @classmethod
    def from_file(cls, path: str) -> Puzzle:
        """Load a Puzzle from a JSON file path."""
        with Path(path).open() as f:
            return cls.from_json(json.load(f))


# ── Solver ───────────────────────────────────────────────────────────


def solve(puzzle: Puzzle) -> list[str] | None:
    """BFS over (position, active_locks) states.  Returns move list or None."""
    initial_locks = frozenset(
        sq.pos for sq in puzzle.squares.values() if sq.square_type == SquareType.LOCK
    )
    start = State(puzzle.player_start, initial_locks)

    queue: deque[tuple[State, list[str]]] = deque([(start, [])])
    visited: set[State] = {start}

    while queue:
        state, path = queue.popleft()

        for dir_name, (dr, dc) in DIRECTIONS.items():
            result = _simulate_move(puzzle, state, dr, dc)
            if result is None:
                continue

            new_state, reached_goal = result
            if reached_goal:
                return [*path, dir_name]
            if new_state not in visited:
                visited.add(new_state)
                queue.append((new_state, [*path, dir_name]))

    return None


def _simulate_move(
    puzzle: Puzzle,
    state: State,
    dr: int,
    dc: int,
) -> tuple[State, bool] | None:
    """Slide in (dr, dc).  Returns (new_state, is_goal) or None on death."""
    r, c = state.pos
    min_r, max_r, min_c, max_c = puzzle.grid_bounds
    approach_side = DIR_TO_APPROACH_SIDE[(dr, dc)]

    cr, cc = r + dr, c + dc
    while min_r <= cr <= max_r and min_c <= cc <= max_c:
        pos = (cr, cc)

        if pos in puzzle.squares:
            sq = puzzle.squares[pos]

            # Vanished lock - slide through
            if sq.square_type == SquareType.LOCK and pos not in state.active_locks:
                cr += dr
                cc += dc
                continue

            # Portal pass-through when approached from marked side
            if sq.square_type == SquareType.PORTAL and sq.portal_side == approach_side:
                cr += dr
                cc += dc
                continue

            # ── Landing ──
            if sq.square_type == SquareType.GOAL:
                return State(pos, state.active_locks), True

            if (
                sq.square_type == SquareType.TELEPORTER
                and pos in puzzle.teleporter_pairs
            ):
                return State(puzzle.teleporter_pairs[pos], state.active_locks), False

            if sq.square_type == SquareType.KEY and pos in puzzle.key_to_lock:
                lock_pos = puzzle.key_to_lock[pos]
                return State(pos, state.active_locks - {lock_pos}), False

            # Default: land on square
            return State(pos, state.active_locks), False

        cr += dr
        cc += dc

    return None  # off-grid → death


# ── Pretty-print ─────────────────────────────────────────────────────

_TYPE_CHAR = {
    SquareType.NORMAL: ".",
    SquareType.PLAYER: "P",
    SquareType.GOAL: "G",
    SquareType.PORTAL: "O",
    SquareType.TELEPORTER: "T",
    SquareType.KEY: "K",
    SquareType.LOCK: "L",
}


def print_puzzle(puzzle: Puzzle) -> None:
    """Print an ASCII representation of the puzzle grid."""
    min_r, max_r, min_c, max_c = puzzle.grid_bounds
    for r in range(min_r + 1, max_r):
        row_chars: list[str] = []
        for c in range(min_c + 1, max_c):
            if (r, c) in puzzle.squares:
                sq = puzzle.squares[(r, c)]
                ch = _TYPE_CHAR.get(sq.square_type, "?")
                if sq.square_type == SquareType.PORTAL and sq.portal_side:
                    arrow = {"left": "<", "right": ">", "up": "^", "down": "v"}
                    ch = arrow.get(sq.portal_side, "O")
                row_chars.append(ch)
            else:
                row_chars.append(" ")


def print_solution(puzzle: Puzzle, moves: list[str]) -> None:
    """Print the solution path step by step."""
    state = State(
        puzzle.player_start,
        frozenset(
            sq.pos
            for sq in puzzle.squares.values()
            if sq.square_type == SquareType.LOCK
        ),
    )
    for _i, move in enumerate(moves, 1):
        dr, dc = DIRECTIONS[move]
        result = _simulate_move(puzzle, state, dr, dc)
        if result is None:
            return
        state, goal = result
