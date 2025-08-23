#!/usr/bin/env python3
"""
Generate pytest cases from a lichess analysis log.

Input: a log file that contains a "Columns:" section and a "PGN:" section,
like the example the user provided. We'll extract each row where class==Blunder,
reconstruct the FEN of the position before the blunder, and the blunder move in
UCI. Then we write a parametrized pytest that asserts the engine does not pick
that same blunder move from that position.

Usage:
  python PYTHON/lichess_bot/tools/generate_blunder_tests.py /path/to/lichess_bot_game_xxxxx.log

It will create a file like:
  PYTHON/lichess_bot/tests/test_blunders_<gameid>.py

Dependencies: python-chess, pytest (already in requirements.txt)
"""

from __future__ import annotations

import io
import os
import re
import sys
from dataclasses import dataclass
from typing import List, Tuple

import chess
import chess.pgn


@dataclass
class Blunder:
    ply: int
    side: str  # 'W' or 'B'
    san: str   # SAN of the played blunder


def parse_columns_for_blunders(text: str) -> List[Blunder]:
    lines = text.splitlines()
    # Find start of "Columns:" block
    try:
        idx = next(i for i, ln in enumerate(lines) if ln.strip().startswith("Columns:"))
    except StopIteration:
        return []

    blunders: List[Blunder] = []
    # Lines after header until a blank line or "PGN:" marker
    for ln in lines[idx + 1:]:
        if not ln.strip():
            break
        if ln.strip().startswith("PGN:"):
            break
        # Expect lines starting with a move number
        if not re.match(r"^\s*\d+\s+", ln):
            continue
        # Split by 2+ spaces to get columns
        parts = re.split(r"\s{2,}", ln.strip())
        # Expected columns: ply, side, move, played_eval, best_eval, loss, class, best_suggestion
        if len(parts) < 7:
            continue
        try:
            ply = int(parts[0])
        except ValueError:
            continue
        side = parts[1]
        move_san = parts[2]
        clazz = parts[6]
        if clazz == "Blunder":
            blunders.append(Blunder(ply=ply, side=side, san=move_san))
    return blunders


def extract_pgn(text: str) -> str | None:
    # Extract the PGN block after a line that is exactly 'PGN:' or starts with it
    m = re.search(r"^PGN:\s*$", text, flags=re.M)
    if not m:
        return None
    start = m.end()
    pgn = text[start:].strip()
    return pgn if pgn else None


def san_list_from_game(game: chess.pgn.Game) -> List[str]:
    san_moves: List[str] = []
    node = game
    while node.variations:
        node = node.variation(0)
        san_moves.append(node.san())
    return san_moves


def fen_and_uci_for_blunders(pgn_text: str, blunders: List[Blunder]) -> List[Tuple[str, str, Blunder]]:
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if game is None:
        raise RuntimeError("Failed to parse PGN from log")

    main_sans = san_list_from_game(game)
    results: List[Tuple[str, str, Blunder]] = []
    for bl in blunders:
        # Reconstruct the board before this ply
        board = game.board()
        # plies are 1-based; apply moves up to ply-1
        upto = max(0, bl.ply - 1)
        for i in range(min(upto, len(main_sans))):
            board.push_san(main_sans[i])
        fen_before = board.fen()
        # Parse the SAN blunder at this position to get UCI. If parse fails, skip.
        try:
            move = board.parse_san(bl.san)
        except ValueError:
            # Try to fall back to using the game's move at that ply if available
            if bl.ply - 1 < len(main_sans):
                try:
                    move = board.parse_san(main_sans[bl.ply - 1])
                except Exception:
                    continue
            else:
                continue
        results.append((fen_before, move.uci(), bl))
    return results


def write_pytest(target_path: str, cases: List[Tuple[str, str, Blunder]], game_id: str):
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(
            """import os
import sys
import chess
import pytest

# Ensure repo root is importable when running pytest directly
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from PYTHON.lichess_bot.engine import RandomEngine  # noqa: E402

BLUNDER_CASES = [
"""
        )
        for fen, uci, bl in cases:
            label = f"ply{bl.ply}_{'W' if bl.side=='W' else 'B'}_{uci}"
            f.write(f"    (\"{fen}\", \"{uci}\", \"{label}\"),\n")
        f.write(
            "]\n\n"
            "@pytest.mark.parametrize('fen,blunder_uci,label', BLUNDER_CASES, ids=[c[2] for c in BLUNDER_CASES])\n"
            "def test_engine_avoids_logged_blunder(fen, blunder_uci, label):\n"
            "    board = chess.Board(fen)\n"
            "    eng = RandomEngine(depth=4, max_time_sec=1.2)\n"
            "    # Prefer explanation variant if available for better failure messages\n"
            "    move = None\n"
            "    explanation = ''\n"
            "    if hasattr(eng, 'choose_move_with_explanation'):\n"
            "        try:\n"
            "            mv, expl = eng.choose_move_with_explanation(board, time_budget_sec=1.2)\n"
            "            move, explanation = mv, expl or ''\n"
            "        except Exception:\n"
            "            move = eng.choose_move(board)\n"
            "    else:\n"
            "        move = eng.choose_move(board)\n"
            "    assert move is not None, 'Engine returned no move'\n"
            "    assert move in board.legal_moves, 'Engine move is illegal'\n"
            "    assert move.uci() != blunder_uci, f'Engine repeated blunder {blunder_uci} at {label}. Explanation: {explanation}'\n"
        )
    print(f"Wrote {target_path} with {len(cases)} blunder checks (game {game_id}).")


def main(argv: List[str]) -> int:
    if len(argv) < 2:
        print("Usage: generate_blunder_tests.py /path/to/lichess_bot_game_xxx.log")
        return 2
    log_path = argv[1]
    with open(log_path, "r", encoding="utf-8") as fh:
        text = fh.read()

    blunders = parse_columns_for_blunders(text)
    if not blunders:
        print("No blunders found in the log's Columns section.")
        return 1

    pgn_text = extract_pgn(text)
    if not pgn_text:
        print("No PGN section found in the log.")
        return 1

    cases = fen_and_uci_for_blunders(pgn_text, blunders)
    if not cases:
        print("Failed to reconstruct any blunder positions from PGN.")
        return 1

    # Try to derive game id from file name
    base = os.path.basename(log_path)
    m = re.search(r"game_([A-Za-z0-9]+)\.log$", base)
    game_id = m.group(1) if m else os.path.splitext(base)[0]

    target = os.path.join(os.path.dirname(__file__), "..", "tests", f"test_blunders_{game_id}.py")
    target = os.path.abspath(target)
    write_pytest(target, cases, game_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
