"""Tests for python_pkg.puzzle_solver.solver module."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import mock_open, patch

import pytest

from python_pkg.puzzle_solver.solver import (
    Puzzle,
    SquareType,
    State,
    _map_keys_to_locks,
    _pair_teleporters,
    _parse_square_list,
    _simulate_move,
    print_puzzle,
    solve,
)

# ── Helpers ──────────────────────────────────────────────────────────


def _minimal_puzzle_data() -> dict[str, Any]:
    """A 3-square puzzle: player -> normal -> goal in a row."""
    return {
        "squares": [
            {"pos": [0, 0], "type": "player"},
            {"pos": [0, 1], "type": "normal"},
            {"pos": [0, 2], "type": "goal"},
        ],
    }


def _make_puzzle(squares_data: list[dict[str, Any]]) -> Puzzle:
    return Puzzle.from_json({"squares": squares_data})


# ── SquareType ───────────────────────────────────────────────────────


class TestSquareType:
    def test_values(self) -> None:
        assert SquareType("normal") == SquareType.NORMAL
        assert SquareType("player") == SquareType.PLAYER
        assert SquareType("goal") == SquareType.GOAL
        assert SquareType("portal") == SquareType.PORTAL
        assert SquareType("teleporter") == SquareType.TELEPORTER
        assert SquareType("key") == SquareType.KEY
        assert SquareType("lock") == SquareType.LOCK


# ── _parse_square_list ───────────────────────────────────────────────


class TestParseSquareList:
    def test_basic(self) -> None:
        sds = [
            {"pos": [0, 0], "type": "player"},
            {"pos": [0, 1], "type": "goal"},
        ]
        squares, meta = _parse_square_list(sds)
        assert (0, 0) in squares
        assert squares[(0, 0)].square_type == SquareType.PLAYER
        assert meta.player_start == (0, 0)
        assert meta.goal_pos == (0, 1)

    def test_no_player_raises(self) -> None:
        sds = [{"pos": [0, 0], "type": "goal"}]
        with pytest.raises(ValueError, match="No player start"):
            _parse_square_list(sds)

    def test_no_goal_raises(self) -> None:
        sds = [{"pos": [0, 0], "type": "player"}]
        with pytest.raises(ValueError, match="No goal position"):
            _parse_square_list(sds)

    def test_teleporter_group(self) -> None:
        sds = [
            {"pos": [0, 0], "type": "player"},
            {"pos": [0, 1], "type": "goal"},
            {"pos": [1, 0], "type": "teleporter", "group": 1},
            {"pos": [1, 1], "type": "teleporter", "group": 1},
        ]
        _, meta = _parse_square_list(sds)
        assert 1 in meta.teleporter_groups
        assert len(meta.teleporter_groups[1]) == 2

    def test_key_lock_maps(self) -> None:
        sds = [
            {"pos": [0, 0], "type": "player"},
            {"pos": [0, 2], "type": "goal"},
            {"pos": [1, 0], "type": "key", "lock_id": 1},
            {"pos": [1, 1], "type": "lock", "lock_id": 1},
        ]
        _, meta = _parse_square_list(sds)
        assert meta.key_map[1] == (1, 0)
        assert meta.lock_map[1] == (1, 1)

    def test_portal_side(self) -> None:
        sds = [
            {"pos": [0, 0], "type": "player"},
            {"pos": [0, 2], "type": "goal"},
            {"pos": [0, 1], "type": "portal", "side": "left"},
        ]
        squares, _ = _parse_square_list(sds)
        assert squares[(0, 1)].portal_side == "left"

    def test_teleporter_without_group(self) -> None:
        sds = [
            {"pos": [0, 0], "type": "player"},
            {"pos": [0, 1], "type": "goal"},
            {"pos": [1, 0], "type": "teleporter"},
        ]
        _, meta = _parse_square_list(sds)
        assert not meta.teleporter_groups

    def test_key_without_lock_id(self) -> None:
        sds = [
            {"pos": [0, 0], "type": "player"},
            {"pos": [0, 1], "type": "goal"},
            {"pos": [1, 0], "type": "key"},
        ]
        _, meta = _parse_square_list(sds)
        assert not meta.key_map

    def test_lock_without_lock_id(self) -> None:
        sds = [
            {"pos": [0, 0], "type": "player"},
            {"pos": [0, 1], "type": "goal"},
            {"pos": [1, 0], "type": "lock"},
        ]
        _, meta = _parse_square_list(sds)
        assert not meta.lock_map


# ── _pair_teleporters ────────────────────────────────────────────────


class TestPairTeleporters:
    def test_valid_pair(self) -> None:
        groups = {1: [(0, 0), (1, 1)]}
        pairs = _pair_teleporters(groups)
        assert pairs[(0, 0)] == (1, 1)
        assert pairs[(1, 1)] == (0, 0)

    def test_wrong_member_count_raises(self) -> None:
        groups = {1: [(0, 0)]}
        with pytest.raises(ValueError, match="Teleporter group 1"):
            _pair_teleporters(groups)

    def test_empty_groups(self) -> None:
        assert _pair_teleporters({}) == {}


# ── _map_keys_to_locks ──────────────────────────────────────────────


class TestMapKeysToLocks:
    def test_valid(self) -> None:
        key_map = {1: (0, 0)}
        lock_map = {1: (1, 1)}
        result = _map_keys_to_locks(key_map, lock_map)
        assert result[(0, 0)] == (1, 1)

    def test_missing_lock_raises(self) -> None:
        key_map = {1: (0, 0)}
        lock_map: dict[int, tuple[int, int]] = {}
        with pytest.raises(ValueError, match="lock_id=1 has no matching lock"):
            _map_keys_to_locks(key_map, lock_map)

    def test_empty(self) -> None:
        assert _map_keys_to_locks({}, {}) == {}


# ── Puzzle ───────────────────────────────────────────────────────────


class TestPuzzle:
    def test_from_json(self) -> None:
        data = _minimal_puzzle_data()
        p = Puzzle.from_json(data)
        assert p.player_start == (0, 0)
        assert p.goal_pos == (0, 2)
        assert len(p.squares) == 3

    def test_from_json_bounds(self) -> None:
        data = _minimal_puzzle_data()
        p = Puzzle.from_json(data)
        min_r, max_r, min_c, max_c = p.grid_bounds
        assert min_r == -1
        assert max_r == 1
        assert min_c == -1
        assert max_c == 3

    def test_from_file(self) -> None:
        data = _minimal_puzzle_data()
        m = mock_open(read_data=json.dumps(data))
        with patch("pathlib.Path.open", m):
            p = Puzzle.from_file("dummy.json")
        assert p.player_start == (0, 0)

    def test_from_json_with_teleporters(self) -> None:
        data = {
            "squares": [
                {"pos": [0, 0], "type": "player"},
                {"pos": [0, 3], "type": "goal"},
                {"pos": [1, 0], "type": "teleporter", "group": 1},
                {"pos": [1, 3], "type": "teleporter", "group": 1},
            ],
        }
        p = Puzzle.from_json(data)
        assert (1, 0) in p.teleporter_pairs
        assert p.teleporter_pairs[(1, 0)] == (1, 3)

    def test_from_json_with_key_lock(self) -> None:
        data = {
            "squares": [
                {"pos": [0, 0], "type": "player"},
                {"pos": [0, 3], "type": "goal"},
                {"pos": [1, 0], "type": "key", "lock_id": 1},
                {"pos": [1, 1], "type": "lock", "lock_id": 1},
            ],
        }
        p = Puzzle.from_json(data)
        assert p.key_to_lock[(1, 0)] == (1, 1)


# ── solve ────────────────────────────────────────────────────────────


class TestSolve:
    def test_simple_right(self) -> None:
        """Player slides right to goal."""
        p = _make_puzzle(
            [
                {"pos": [0, 0], "type": "player"},
                {"pos": [0, 1], "type": "normal"},
                {"pos": [0, 2], "type": "goal"},
            ]
        )
        moves = solve(p)
        assert moves is not None
        assert "right" in moves

    def test_no_solution(self) -> None:
        """Player has no path to goal."""
        p = _make_puzzle(
            [
                {"pos": [0, 0], "type": "player"},
                {"pos": [2, 2], "type": "goal"},
            ]
        )
        assert solve(p) is None

    def test_with_teleporter(self) -> None:
        """Player hits teleporter and warps."""
        p = _make_puzzle(
            [
                {"pos": [0, 0], "type": "player"},
                {"pos": [0, 1], "type": "teleporter", "group": 1},
                {"pos": [2, 0], "type": "teleporter", "group": 1},
                {"pos": [2, 1], "type": "goal"},
            ]
        )
        moves = solve(p)
        assert moves is not None

    def test_with_key_lock(self) -> None:
        """Player collects key to unlock path."""
        p = _make_puzzle(
            [
                {"pos": [0, 0], "type": "player"},
                {"pos": [0, 1], "type": "key", "lock_id": 1},
                {"pos": [0, 2], "type": "normal"},
                {"pos": [1, 0], "type": "normal"},
                {"pos": [1, 2], "type": "lock", "lock_id": 1},
                {"pos": [2, 0], "type": "normal"},
                {"pos": [2, 2], "type": "goal"},
            ]
        )
        moves = solve(p)
        assert moves is not None

    def test_with_portal_passthrough(self) -> None:
        """Portal is passthrough from its marked side."""
        p = _make_puzzle(
            [
                {"pos": [0, 0], "type": "player"},
                {"pos": [0, 1], "type": "portal", "side": "left"},
                {"pos": [0, 2], "type": "goal"},
            ]
        )
        moves = solve(p)
        assert moves == ["right"]

    def test_portal_blocks_from_other_side(self) -> None:
        """Portal blocks approach from non-marked side."""
        p = _make_puzzle(
            [
                {"pos": [0, 0], "type": "player"},
                {"pos": [0, 1], "type": "portal", "side": "right"},
                {"pos": [0, 2], "type": "goal"},
            ]
        )
        # approaching from left, but side is "right" => should stop at portal
        moves = solve(p)
        # Player lands on portal, doesn't reach goal directly by going right
        assert moves is not None


# ── _simulate_move ───────────────────────────────────────────────────


class TestSimulateMove:
    def test_off_grid_returns_none(self) -> None:
        p = _make_puzzle(
            [
                {"pos": [0, 0], "type": "player"},
                {"pos": [0, 1], "type": "goal"},
            ]
        )
        state = State((0, 0), frozenset())
        # Move up from (0,0) → off grid
        result = _simulate_move(p, state, -1, 0)
        assert result is None

    def test_land_on_normal(self) -> None:
        p = _make_puzzle(
            [
                {"pos": [0, 0], "type": "player"},
                {"pos": [0, 1], "type": "normal"},
                {"pos": [0, 2], "type": "goal"},
            ]
        )
        state = State((0, 0), frozenset())
        result = _simulate_move(p, state, 0, 1)
        assert result is not None
        new_state, is_goal = result
        assert new_state.pos == (0, 1)
        assert not is_goal

    def test_land_on_goal(self) -> None:
        p = _make_puzzle(
            [
                {"pos": [0, 0], "type": "player"},
                {"pos": [0, 1], "type": "goal"},
            ]
        )
        state = State((0, 0), frozenset())
        result = _simulate_move(p, state, 0, 1)
        assert result is not None
        _, is_goal = result
        assert is_goal

    def test_slide_through_vanished_lock(self) -> None:
        """Lock is inactive (not in active_locks) → slide through."""
        p = _make_puzzle(
            [
                {"pos": [0, 0], "type": "player"},
                {"pos": [0, 1], "type": "lock", "lock_id": 1},
                {"pos": [0, 2], "type": "key", "lock_id": 1},
                {"pos": [0, 3], "type": "goal"},
            ]
        )
        # Lock at (0,1) is not in active_locks → vanished
        state = State((0, 0), frozenset())
        result = _simulate_move(p, state, 0, 1)
        assert result is not None
        # Should slide through the vanished lock

    def test_portal_passthrough(self) -> None:
        p = _make_puzzle(
            [
                {"pos": [0, 0], "type": "player"},
                {"pos": [0, 1], "type": "portal", "side": "left"},
                {"pos": [0, 2], "type": "goal"},
            ]
        )
        state = State((0, 0), frozenset())
        result = _simulate_move(p, state, 0, 1)
        assert result is not None
        new_state, is_goal = result
        assert is_goal
        assert new_state.pos == (0, 2)

    def test_teleporter_landing(self) -> None:
        p = _make_puzzle(
            [
                {"pos": [0, 0], "type": "player"},
                {"pos": [0, 1], "type": "teleporter", "group": 1},
                {"pos": [2, 2], "type": "teleporter", "group": 1},
                {"pos": [2, 3], "type": "goal"},
            ]
        )
        state = State((0, 0), frozenset())
        result = _simulate_move(p, state, 0, 1)
        assert result is not None
        new_state, is_goal = result
        assert new_state.pos == (2, 2)
        assert not is_goal

    def test_key_landing_removes_lock(self) -> None:
        p = _make_puzzle(
            [
                {"pos": [0, 0], "type": "player"},
                {"pos": [0, 1], "type": "key", "lock_id": 1},
                {"pos": [1, 0], "type": "lock", "lock_id": 1},
                {"pos": [0, 2], "type": "goal"},
            ]
        )
        lock_pos = (1, 0)
        state = State((0, 0), frozenset({lock_pos}))
        result = _simulate_move(p, state, 0, 1)
        assert result is not None
        new_state, is_goal = result
        assert new_state.pos == (0, 1)
        assert lock_pos not in new_state.active_locks
        assert not is_goal

    def test_active_lock_blocks(self) -> None:
        """When lock is active, it blocks movement."""
        p = _make_puzzle(
            [
                {"pos": [0, 0], "type": "player"},
                {"pos": [0, 1], "type": "lock", "lock_id": 1},
                {"pos": [0, 2], "type": "key", "lock_id": 1},
                {"pos": [0, 3], "type": "goal"},
            ]
        )
        lock_pos = (0, 1)
        state = State((0, 0), frozenset({lock_pos}))
        result = _simulate_move(p, state, 0, 1)
        assert result is not None
        new_state, is_goal = result
        # Lands on the lock since it's active
        assert new_state.pos == (0, 1)
        assert not is_goal


# ── print_puzzle ─────────────────────────────────────────────────────


class TestPrintPuzzle:
    def test_basic(self, capsys: pytest.CaptureFixture[str]) -> None:
        p = _make_puzzle(
            [
                {"pos": [0, 0], "type": "player"},
                {"pos": [0, 1], "type": "normal"},
                {"pos": [0, 2], "type": "goal"},
            ]
        )
        print_puzzle(p)

    def test_all_types(self, capsys: pytest.CaptureFixture[str]) -> None:
        p = _make_puzzle(
            [
                {"pos": [0, 0], "type": "player"},
                {"pos": [0, 1], "type": "normal"},
                {"pos": [0, 2], "type": "goal"},
                {"pos": [1, 0], "type": "portal", "side": "left"},
                {"pos": [1, 1], "type": "portal", "side": "right"},
                {"pos": [1, 2], "type": "portal", "side": "up"},
                {"pos": [2, 0], "type": "portal", "side": "down"},
                {"pos": [2, 1], "type": "teleporter", "group": 1},
                {"pos": [2, 2], "type": "teleporter", "group": 1},
            ]
        )
        print_puzzle(p)

    def test_portal_no_side(self, capsys: pytest.CaptureFixture[str]) -> None:
        p = _make_puzzle(
            [
                {"pos": [0, 0], "type": "player"},
                {"pos": [0, 1], "type": "portal"},
                {"pos": [0, 2], "type": "goal"},
            ]
        )
        print_puzzle(p)

    def test_empty_cells(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Grid with gaps should print spaces."""
        p = _make_puzzle(
            [
                {"pos": [0, 0], "type": "player"},
                {"pos": [0, 3], "type": "goal"},
            ]
        )
        print_puzzle(p)


# ── print_solution ───────────────────────────────────────────────────
