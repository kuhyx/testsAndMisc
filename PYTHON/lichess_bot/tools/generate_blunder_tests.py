#!/usr/bin/env python3
"""
Generate pytest cases from one or more lichess analysis logs.

Input: log files that contain a "Columns:" section and a "PGN:" section.
We'll extract each row where class==Blunder, reconstruct the FEN of the
position before the blunder, and the blunder move in UCI. Then we'll write
parametrized pytest files that assert the engine does not pick that same
blunder move from those positions.

Where logs are loaded from:
    - By default (no arguments), all logs in the "past_games" folder located
        next to this script will be processed (files matching lichess_bot_game_*.log).
    - If a single argument is provided and it's a file path, that file is used.
    - If a single argument looks like a game id (e.g. OVmR29MI), the script will
        look for past_games/lichess_bot_game_<gameid>.log next to this script.

Usage examples:
    # Process all logs in tools/past_games
    python PYTHON/lichess_bot/tools/generate_blunder_tests.py

    # Process a specific game by id from tools/past_games
    python PYTHON/lichess_bot/tools/generate_blunder_tests.py OVmR29MI

    # Process an explicit file path
    python PYTHON/lichess_bot/tools/generate_blunder_tests.py /path/to/lichess_bot_game_xxxxx.log

It will create files like:
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


def ensure_unified_test_file(target_path: str) -> None:
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    if os.path.exists(target_path):
        return
    # Create skeleton unified test file
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
]


@pytest.mark.parametrize('fen,blunder_uci,label', BLUNDER_CASES, ids=[c[2] for c in BLUNDER_CASES])
def test_engine_avoids_logged_blunder(fen, blunder_uci, label):
    board = chess.Board(fen)
    eng = RandomEngine(depth=4, max_time_sec=1.2)
    # Prefer explanation variant if available for better failure messages
    move = None
    explanation = ''
    if hasattr(eng, 'choose_move_with_explanation'):
        try:
            mv, expl = eng.choose_move_with_explanation(board, time_budget_sec=1.2)
            move, explanation = mv, expl or ''
        except Exception:
            move = eng.choose_move(board)
    else:
        move = eng.choose_move(board)
    assert move is not None, 'Engine returned no move'
    assert move in board.legal_moves, 'Engine move is illegal'
    assert move.uci() != blunder_uci, f'Engine repeated blunder {blunder_uci} at {label}. Explanation: {explanation}'
"""
        )


def append_cases_to_unified_test(unified_path: str, cases: List[Tuple[str, str, Blunder]]) -> int:
    """Append new cases to BLUNDER_CASES in the unified test file, skipping duplicates.

    Returns the number of cases actually appended.
    """
    ensure_unified_test_file(unified_path)
    with open(unified_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Extract current cases as a set of (fen, uci) to de-duplicate
    existing = set(re.findall(r"\(\"(.*?)\",\s*\"(.*?)\",\s*\"ply\d+_[WB]_[^\"]+\"\)\,?", content, flags=re.S))

    lines = []
    for fen, uci, bl in cases:
        key = (fen, uci)
        if key in existing:
            continue
        label = f"ply{bl.ply}_{'W' if bl.side=='W' else 'B'}_{uci}"
        lines.append(f"    (\"{fen}\", \"{uci}\", \"{label}\"),\n")

    if not lines:
        return 0

    # Insert before closing bracket of BLUNDER_CASES
    new_content = re.sub(
        r"BLUNDER_CASES\s*=\s*\[\n",
        lambda m: m.group(0) + "".join(lines),
        content,
        count=1,
    )

    with open(unified_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    return len(lines)


def _process_single_log(log_path: str) -> int:
    """Process a single log file. Returns 0 on success, non-zero otherwise."""
    try:
        with open(log_path, "r", encoding="utf-8") as fh:
            text = fh.read()
    except FileNotFoundError:
        print(f"Log file not found: {log_path}")
        return 2

    blunders = parse_columns_for_blunders(text)
    if not blunders:
        print(f"No blunders found in Columns section: {os.path.basename(log_path)}")
        return 1

    pgn_text = extract_pgn(text)
    if not pgn_text:
        print(f"No PGN section found: {os.path.basename(log_path)}")
        return 1

    cases = fen_and_uci_for_blunders(pgn_text, blunders)
    if not cases:
        print(f"Failed to reconstruct any blunder positions from PGN: {os.path.basename(log_path)}")
        return 1

    base = os.path.basename(log_path)
    m = re.search(r"game_([A-Za-z0-9]+)\.log$", base)
    game_id = m.group(1) if m else os.path.splitext(base)[0]

    # Always append to the unified test file
    unified = os.path.join(os.path.dirname(__file__), "..", "tests", "test_blunders_all.py")
    unified = os.path.abspath(unified)
    added = append_cases_to_unified_test(unified, cases)
    print(f"Appended {added} new blunder checks to {os.path.relpath(unified)} (game {game_id}).")
    return 0


def main(argv: List[str]) -> int:
    script_dir = os.path.dirname(__file__)
    past_dir = os.path.abspath(os.path.join(script_dir, "past_games"))

    # No argument: process all logs in past_games
    if len(argv) == 1:
        if not os.path.isdir(past_dir):
            print(f"No past_games directory found at {past_dir}")
            return 2
        logs = [
            os.path.join(past_dir, name)
            for name in os.listdir(past_dir)
            if re.match(r"lichess_bot_game_[A-Za-z0-9]+\.log$", name)
        ]
        if not logs:
            print(f"No logs found in {past_dir}")
            return 1
        # Sort by mtime ascending for determinism
        logs.sort(key=lambda p: os.path.getmtime(p))
        ok = 0
        for lp in logs:
            rc = _process_single_log(lp)
            if rc == 0:
                ok += 1
        print(f"Processed {len(logs)} logs from {past_dir}, succeeded: {ok}, failed: {len(logs)-ok}")
        return 0 if ok > 0 else 1

    # One argument: game id or file path
    arg = argv[1]
    candidate_path = None
    if os.path.isfile(arg):
        candidate_path = arg
    else:
        # Treat as game id, resolve within past_games
        if re.fullmatch(r"[A-Za-z0-9]+", arg):
            candidate_path = os.path.join(past_dir, f"lichess_bot_game_{arg}.log")
        else:
            # Fallback: if it's a bare filename, try inside past_games
            maybe = os.path.join(past_dir, arg)
            if os.path.isfile(maybe):
                candidate_path = maybe

    if not candidate_path:
        print("Usage: generate_blunder_tests.py [<game_id>|</path/to/log>]")
        return 2

    return _process_single_log(candidate_path)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
