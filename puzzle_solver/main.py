"""CLI for the sliding-square puzzle solver.

Usage
-----
  # 1) Parse a screenshot → JSON  (review & hand-edit if needed)
  python puzzle_solver/main.py parse screenshot.png -o puzzle.json

  # 2) Solve from JSON
  python puzzle_solver/main.py solve puzzle.json

  # 3) One-shot: parse + solve (skip manual review)
  python puzzle_solver/main.py run screenshot.png

  # 4) Draw debug overlay showing detected squares
  python puzzle_solver/main.py debug screenshot.png -o debug.png
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from puzzle_solver.parse_image import draw_debug, parse_image, save_puzzle
from puzzle_solver.solver import Puzzle, print_puzzle, print_solution, solve


def cmd_parse(args: argparse.Namespace) -> None:
    """Parse a screenshot into editable puzzle JSON."""
    puzzle = parse_image(args.image, threshold=args.threshold)
    out = args.output or args.image.rsplit(".", 1)[0] + "_puzzle.json"
    save_puzzle(puzzle, out)
    if puzzle.get("notes"):
        for _n in puzzle["notes"]:
            pass


def cmd_solve(args: argparse.Namespace) -> None:
    """Solve a puzzle from a JSON file."""
    with Path(args.puzzle).open() as f:
        data = json.load(f)
    puzzle = Puzzle.from_json(data)
    print_puzzle(puzzle)
    moves = solve(puzzle)
    if moves is None:
        sys.exit(1)
    print_solution(puzzle, moves)


def cmd_run(args: argparse.Namespace) -> None:
    """Parse a screenshot and solve in one shot."""
    data = parse_image(args.image, threshold=args.threshold)
    if data.get("notes"):
        for _n in data["notes"]:
            pass

    puzzle = Puzzle.from_json(data)
    print_puzzle(puzzle)
    moves = solve(puzzle)
    if moves is None:
        out = args.image.rsplit(".", 1)[0] + "_puzzle.json"
        save_puzzle(data, out)
        sys.exit(1)
    print_solution(puzzle, moves)


def cmd_debug(args: argparse.Namespace) -> None:
    """Draw a debug overlay showing detected square types."""
    data = parse_image(args.image, threshold=args.threshold)
    out = args.output or args.image.rsplit(".", 1)[0] + "_debug.png"
    draw_debug(args.image, data, out)
    from collections import Counter

    counts = Counter(sq["type"] for sq in data["squares"])
    for _t, _n in counts.most_common():
        pass


def main() -> None:
    """Entry point for the puzzle solver CLI."""
    ap = argparse.ArgumentParser(description="Sliding-square puzzle solver")
    sub = ap.add_subparsers(dest="command", required=True)

    p_parse = sub.add_parser("parse", help="Parse screenshot → puzzle JSON")
    p_parse.add_argument("image")
    p_parse.add_argument("-o", "--output", help="Output JSON path")
    p_parse.add_argument("-t", "--threshold", type=int, default=55)

    p_solve = sub.add_parser("solve", help="Solve puzzle from JSON")
    p_solve.add_argument("puzzle", help="Puzzle JSON file")

    p_run = sub.add_parser("run", help="Parse + solve in one shot")
    p_run.add_argument("image")
    p_run.add_argument("-t", "--threshold", type=int, default=55)

    p_debug = sub.add_parser("debug", help="Draw debug overlay on image")
    p_debug.add_argument("image")
    p_debug.add_argument("-o", "--output", help="Output image path")
    p_debug.add_argument("-t", "--threshold", type=int, default=55)

    args = ap.parse_args()
    {"parse": cmd_parse, "solve": cmd_solve, "run": cmd_run, "debug": cmd_debug}[
        args.command
    ](args)


if __name__ == "__main__":
    main()
