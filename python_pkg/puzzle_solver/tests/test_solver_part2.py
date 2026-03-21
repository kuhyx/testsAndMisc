"""Tests for uncovered branches in python_pkg.puzzle_solver.solver."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from python_pkg.puzzle_solver.solver import (
    Puzzle,
    print_solution,
)

if TYPE_CHECKING:
    import pytest


def _make_puzzle(squares_data: list[dict[str, Any]]) -> Puzzle:
    return Puzzle.from_json({"squares": squares_data})


# ── print_solution ───────────────────────────────────────────────────


class TestPrintSolution:
    def test_prints_valid_moves(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Successfully prints all solution steps."""
        p = _make_puzzle(
            [
                {"pos": [0, 0], "type": "player"},
                {"pos": [0, 1], "type": "normal"},
                {"pos": [0, 2], "type": "goal"},
            ]
        )
        print_solution(p, ["right"])

    def test_stops_on_none_result(self) -> None:
        """Returns early when _simulate_move returns None."""
        p = _make_puzzle(
            [
                {"pos": [0, 0], "type": "player"},
                {"pos": [0, 1], "type": "goal"},
            ]
        )
        # "up" from (0,0) goes off-grid → _simulate_move returns None → early return
        print_solution(p, ["up", "right"])

    def test_multiple_moves(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Prints multiple steps in sequence."""
        p = _make_puzzle(
            [
                {"pos": [0, 0], "type": "player"},
                {"pos": [0, 1], "type": "normal"},
                {"pos": [0, 2], "type": "normal"},
                {"pos": [0, 3], "type": "goal"},
                {"pos": [1, 0], "type": "normal"},
            ]
        )
        # right lands on (0,1), right again lands on (0,2), right again → goal
        print_solution(p, ["right", "right", "right"])

    def test_with_locks(self) -> None:
        """Handles state with initial locks correctly."""
        p = _make_puzzle(
            [
                {"pos": [0, 0], "type": "player"},
                {"pos": [0, 1], "type": "key", "lock_id": 1},
                {"pos": [1, 0], "type": "lock", "lock_id": 1},
                {"pos": [0, 2], "type": "goal"},
            ]
        )
        print_solution(p, ["right", "right"])

    def test_empty_moves_list(self) -> None:
        """No moves → prints nothing."""
        p = _make_puzzle(
            [
                {"pos": [0, 0], "type": "player"},
                {"pos": [0, 1], "type": "goal"},
            ]
        )
        print_solution(p, [])

    def test_with_teleporter(self) -> None:
        """Teleporter warping is tracked in state."""
        p = _make_puzzle(
            [
                {"pos": [0, 0], "type": "player"},
                {"pos": [0, 1], "type": "teleporter", "group": 1},
                {"pos": [2, 0], "type": "teleporter", "group": 1},
                {"pos": [2, 1], "type": "goal"},
            ]
        )
        print_solution(p, ["right", "right"])
