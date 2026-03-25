"""Tests for python_pkg.puzzle_solver.main and __main__ modules."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, mock_open, patch

import pytest

from python_pkg.puzzle_solver.main import (
    cmd_debug,
    cmd_parse,
    cmd_run,
    cmd_solve,
    main,
)


def _minimal_puzzle_data() -> dict[str, Any]:
    return {
        "squares": [
            {"pos": [0, 0], "type": "player"},
            {"pos": [0, 1], "type": "normal"},
            {"pos": [0, 2], "type": "goal"},
        ],
    }


# ── cmd_parse ────────────────────────────────────────────────────────


class TestCmdParse:
    @patch("python_pkg.puzzle_solver.main.save_puzzle")
    @patch("python_pkg.puzzle_solver.main.parse_image")
    def test_with_output(self, mock_parse: MagicMock, mock_save: MagicMock) -> None:
        mock_parse.return_value = {"squares": [], "notes": []}
        args = MagicMock()
        args.image = "test.png"
        args.output = "out.json"
        args.threshold = 55
        cmd_parse(args)
        mock_save.assert_called_once_with({"squares": [], "notes": []}, "out.json")

    @patch("python_pkg.puzzle_solver.main.save_puzzle")
    @patch("python_pkg.puzzle_solver.main.parse_image")
    def test_default_output(self, mock_parse: MagicMock, mock_save: MagicMock) -> None:
        mock_parse.return_value = {"squares": [], "notes": []}
        args = MagicMock()
        args.image = "screenshot.png"
        args.output = None
        args.threshold = 55
        cmd_parse(args)
        mock_save.assert_called_once_with(
            {"squares": [], "notes": []}, "screenshot_puzzle.json"
        )

    @patch("python_pkg.puzzle_solver.main.save_puzzle")
    @patch("python_pkg.puzzle_solver.main.parse_image")
    def test_with_notes(self, mock_parse: MagicMock, mock_save: MagicMock) -> None:
        mock_parse.return_value = {
            "squares": [],
            "notes": ["note1", "note2"],
        }
        args = MagicMock()
        args.image = "test.png"
        args.output = "out.json"
        args.threshold = 55
        cmd_parse(args)

    @patch("python_pkg.puzzle_solver.main.save_puzzle")
    @patch("python_pkg.puzzle_solver.main.parse_image")
    def test_no_notes(self, mock_parse: MagicMock, mock_save: MagicMock) -> None:
        mock_parse.return_value = {"squares": []}
        args = MagicMock()
        args.image = "test.png"
        args.output = "out.json"
        args.threshold = 55
        cmd_parse(args)


# ── cmd_solve ────────────────────────────────────────────────────────


class TestCmdSolve:
    @patch("python_pkg.puzzle_solver.main.print_solution")
    @patch("python_pkg.puzzle_solver.main.solve")
    @patch("python_pkg.puzzle_solver.main.print_puzzle")
    @patch("python_pkg.puzzle_solver.main.Puzzle")
    def test_solvable(
        self,
        mock_puzzle_cls: MagicMock,
        mock_print: MagicMock,
        mock_solve: MagicMock,
        mock_print_sol: MagicMock,
    ) -> None:
        data = _minimal_puzzle_data()
        m = mock_open(read_data=json.dumps(data))
        mock_puzzle = MagicMock()
        mock_puzzle_cls.from_json.return_value = mock_puzzle
        mock_solve.return_value = ["right"]

        with patch("pathlib.Path.open", m):
            args = MagicMock()
            args.puzzle = "test.json"
            cmd_solve(args)
        mock_print_sol.assert_called_once()

    @patch("python_pkg.puzzle_solver.main.solve")
    @patch("python_pkg.puzzle_solver.main.print_puzzle")
    @patch("python_pkg.puzzle_solver.main.Puzzle")
    def test_unsolvable(
        self,
        mock_puzzle_cls: MagicMock,
        mock_print: MagicMock,
        mock_solve: MagicMock,
    ) -> None:
        data = _minimal_puzzle_data()
        m = mock_open(read_data=json.dumps(data))
        mock_puzzle = MagicMock()
        mock_puzzle_cls.from_json.return_value = mock_puzzle
        mock_solve.return_value = None

        args = MagicMock()
        args.puzzle = "test.json"
        with patch("pathlib.Path.open", m), pytest.raises(SystemExit):
            cmd_solve(args)


# ── cmd_run ──────────────────────────────────────────────────────────


class TestCmdRun:
    @patch("python_pkg.puzzle_solver.main.print_solution")
    @patch("python_pkg.puzzle_solver.main.solve")
    @patch("python_pkg.puzzle_solver.main.print_puzzle")
    @patch("python_pkg.puzzle_solver.main.Puzzle")
    @patch("python_pkg.puzzle_solver.main.parse_image")
    def test_solvable(
        self,
        mock_parse: MagicMock,
        mock_puzzle_cls: MagicMock,
        mock_print: MagicMock,
        mock_solve: MagicMock,
        mock_print_sol: MagicMock,
    ) -> None:
        mock_parse.return_value = _minimal_puzzle_data()
        mock_puzzle = MagicMock()
        mock_puzzle_cls.from_json.return_value = mock_puzzle
        mock_solve.return_value = ["right"]

        args = MagicMock()
        args.image = "test.png"
        args.threshold = 55
        cmd_run(args)
        mock_print_sol.assert_called_once()

    @patch("python_pkg.puzzle_solver.main.save_puzzle")
    @patch("python_pkg.puzzle_solver.main.solve")
    @patch("python_pkg.puzzle_solver.main.print_puzzle")
    @patch("python_pkg.puzzle_solver.main.Puzzle")
    @patch("python_pkg.puzzle_solver.main.parse_image")
    def test_unsolvable(
        self,
        mock_parse: MagicMock,
        mock_puzzle_cls: MagicMock,
        mock_print: MagicMock,
        mock_solve: MagicMock,
        mock_save: MagicMock,
    ) -> None:
        mock_parse.return_value = _minimal_puzzle_data()
        mock_puzzle = MagicMock()
        mock_puzzle_cls.from_json.return_value = mock_puzzle
        mock_solve.return_value = None

        args = MagicMock()
        args.image = "test.png"
        args.threshold = 55
        with pytest.raises(SystemExit):
            cmd_run(args)
        mock_save.assert_called_once()

    @patch("python_pkg.puzzle_solver.main.print_solution")
    @patch("python_pkg.puzzle_solver.main.solve")
    @patch("python_pkg.puzzle_solver.main.print_puzzle")
    @patch("python_pkg.puzzle_solver.main.Puzzle")
    @patch("python_pkg.puzzle_solver.main.parse_image")
    def test_with_notes(
        self,
        mock_parse: MagicMock,
        mock_puzzle_cls: MagicMock,
        mock_print: MagicMock,
        mock_solve: MagicMock,
        mock_print_sol: MagicMock,
    ) -> None:
        data = _minimal_puzzle_data()
        data["notes"] = ["note1"]
        mock_parse.return_value = data
        mock_puzzle = MagicMock()
        mock_puzzle_cls.from_json.return_value = mock_puzzle
        mock_solve.return_value = ["right"]

        args = MagicMock()
        args.image = "test.png"
        args.threshold = 55
        cmd_run(args)

    @patch("python_pkg.puzzle_solver.main.print_solution")
    @patch("python_pkg.puzzle_solver.main.solve")
    @patch("python_pkg.puzzle_solver.main.print_puzzle")
    @patch("python_pkg.puzzle_solver.main.Puzzle")
    @patch("python_pkg.puzzle_solver.main.parse_image")
    def test_no_notes_key(
        self,
        mock_parse: MagicMock,
        mock_puzzle_cls: MagicMock,
        mock_print: MagicMock,
        mock_solve: MagicMock,
        mock_print_sol: MagicMock,
    ) -> None:
        data = _minimal_puzzle_data()
        # no "notes" key at all
        mock_parse.return_value = data
        mock_puzzle = MagicMock()
        mock_puzzle_cls.from_json.return_value = mock_puzzle
        mock_solve.return_value = ["right"]

        args = MagicMock()
        args.image = "test.png"
        args.threshold = 55
        cmd_run(args)


# ── cmd_debug ────────────────────────────────────────────────────────


class TestCmdDebug:
    @patch("python_pkg.puzzle_solver.main.draw_debug")
    @patch("python_pkg.puzzle_solver.main.parse_image")
    def test_with_output(self, mock_parse: MagicMock, mock_draw: MagicMock) -> None:
        mock_parse.return_value = {
            "squares": [
                {"type": "normal"},
                {"type": "normal"},
                {"type": "goal"},
            ],
        }
        args = MagicMock()
        args.image = "test.png"
        args.output = "debug.png"
        args.threshold = 55
        cmd_debug(args)
        mock_draw.assert_called_once_with(
            "test.png", mock_parse.return_value, "debug.png"
        )

    @patch("python_pkg.puzzle_solver.main.draw_debug")
    @patch("python_pkg.puzzle_solver.main.parse_image")
    def test_default_output(self, mock_parse: MagicMock, mock_draw: MagicMock) -> None:
        mock_parse.return_value = {
            "squares": [{"type": "normal"}],
        }
        args = MagicMock()
        args.image = "screenshot.png"
        args.output = None
        args.threshold = 55
        cmd_debug(args)
        mock_draw.assert_called_once_with(
            "screenshot.png", mock_parse.return_value, "screenshot_debug.png"
        )


# ── main ─────────────────────────────────────────────────────────────


class TestMain:
    @patch("python_pkg.puzzle_solver.main.parse_image")
    @patch("python_pkg.puzzle_solver.main.save_puzzle")
    def test_parse_command(self, mock_save: MagicMock, mock_parse: MagicMock) -> None:
        mock_parse.return_value = {"squares": [], "notes": []}
        with patch("sys.argv", ["prog", "parse", "img.png", "-o", "out.json"]):
            main()

    @patch("python_pkg.puzzle_solver.main.print_solution")
    @patch("python_pkg.puzzle_solver.main.solve")
    @patch("python_pkg.puzzle_solver.main.print_puzzle")
    @patch("python_pkg.puzzle_solver.main.Puzzle")
    def test_solve_command(
        self,
        mock_puzzle_cls: MagicMock,
        mock_print: MagicMock,
        mock_solve: MagicMock,
        mock_print_sol: MagicMock,
    ) -> None:
        data = _minimal_puzzle_data()
        m = mock_open(read_data=json.dumps(data))
        mock_puzzle = MagicMock()
        mock_puzzle_cls.from_json.return_value = mock_puzzle
        mock_solve.return_value = ["right"]

        with (
            patch("pathlib.Path.open", m),
            patch("sys.argv", ["prog", "solve", "puzzle.json"]),
        ):
            main()

    @patch("python_pkg.puzzle_solver.main.print_solution")
    @patch("python_pkg.puzzle_solver.main.solve")
    @patch("python_pkg.puzzle_solver.main.print_puzzle")
    @patch("python_pkg.puzzle_solver.main.Puzzle")
    @patch("python_pkg.puzzle_solver.main.parse_image")
    def test_run_command(
        self,
        mock_parse: MagicMock,
        mock_puzzle_cls: MagicMock,
        mock_print: MagicMock,
        mock_solve: MagicMock,
        mock_print_sol: MagicMock,
    ) -> None:
        mock_parse.return_value = _minimal_puzzle_data()
        mock_puzzle = MagicMock()
        mock_puzzle_cls.from_json.return_value = mock_puzzle
        mock_solve.return_value = ["right"]

        with patch("sys.argv", ["prog", "run", "img.png"]):
            main()

    @patch("python_pkg.puzzle_solver.main.draw_debug")
    @patch("python_pkg.puzzle_solver.main.parse_image")
    def test_debug_command(self, mock_parse: MagicMock, mock_draw: MagicMock) -> None:
        mock_parse.return_value = {"squares": [{"type": "normal"}]}
        with patch("sys.argv", ["prog", "debug", "img.png", "-o", "d.png"]):
            main()


# ── __main__.py ──────────────────────────────────────────────────────


class TestDunderMain:
    @patch("python_pkg.puzzle_solver.main.main")
    def test_main_called(self, mock_main: MagicMock) -> None:
        import importlib

        import python_pkg.puzzle_solver.__main__ as mod

        importlib.reload(mod)
        mock_main.assert_called()
