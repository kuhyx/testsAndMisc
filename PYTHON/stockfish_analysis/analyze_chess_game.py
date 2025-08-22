#!/usr/bin/env python3
"""
Analyze a chess game's moves using a local Stockfish engine and rate each move.

Usage:
  python3 PYTHON/analyze_chess_game.py <path-to-file> [--engine stockfish] [--time 0.2 | --depth 12]

Notes:
  - Requires python-chess. Install from PYTHON/stockfish_analysis/requirements.txt
  - The input file can be a pure PGN or a log file containing a PGN section.
  - The script tries to locate the PGN by looking for a 'PGN:' marker, PGN tags '[...]', or a move list starting with '1.'.
"""

from __future__ import annotations

import argparse
import io
import os
import re
import sys
from typing import Optional, Tuple

try:
    import chess
    import chess.engine
    import chess.pgn
except Exception as e:  # pragma: no cover
    print("Missing dependency. Please install python-chess:", file=sys.stderr)
    print("  pip install -r PYTHON/stockfish_analysis/requirements.txt", file=sys.stderr)
    raise


def extract_pgn_text(raw: str) -> Optional[str]:
    """Try to extract a PGN block from a possibly noisy file.

    Strategies tried in order:
      1) Everything after a line that equals or starts with 'PGN:'
      2) From the first PGN tag line '[' to the end
      3) From the first line starting with an integer and a dot (e.g., '1.') to the end
    """
    lines = raw.splitlines()

    # 1) After 'PGN:' marker
    for i, line in enumerate(lines):
        if line.strip().startswith("PGN:"):
            # everything after this line
            pgn = "\n".join(lines[i + 1 :]).strip()
            if pgn:
                return pgn

    # 2) From first tag line
    for i, line in enumerate(lines):
        if line.strip().startswith("[") and "]" in line:
            pgn = "\n".join(lines[i:]).strip()
            if pgn:
                return pgn

    # 3) From first move number
    move_start_re = re.compile(r"^\s*\d+\.")
    for i, line in enumerate(lines):
        if move_start_re.match(line):
            pgn = "\n".join(lines[i:]).strip()
            if pgn:
                return pgn

    return None


def score_to_cp(score: chess.engine.PovScore, pov_white: bool) -> Tuple[Optional[int], Optional[int]]:
    """Return tuple (cp, mate_in) from a PovScore for the given POV color.

    If it's a mate score, cp will be None and mate_in will be +/-N (positive means mate for POV side).
    If it's a cp score, mate_in will be None.
    """
    pov = chess.WHITE if pov_white else chess.BLACK
    s = score.pov(pov)
    if s.is_mate():
        mi = s.mate()
        return None, mi
    return s.score(mate_score=None), None


def classify_cp_loss(cp_loss: Optional[int]) -> str:
    """Classify move quality using Lichess-like centipawn loss bands.

    Loss is best_eval(cp) - played_eval(cp), from the mover's POV (positive is worse).
    Bands (approx, widely cited):
      - Best:    0..10 cp
      - Excellent: 11..20 cp
      - Good:    21..50 cp
      - Inaccuracy: 51..99 cp
      - Mistake: 100..299 cp
      - Blunder: >=300 cp
    """
    if cp_loss is None:
        return "Unknown"
    if cp_loss <= 10:
        return "Best"
    if cp_loss <= 20:
        return "Excellent"
    if cp_loss <= 50:
        return "Good"
    if cp_loss <= 99:
        return "Inaccuracy"
    if cp_loss <= 299:
        return "Mistake"
    return "Blunder"


def fmt_eval(cp: Optional[int], mate_in: Optional[int]) -> str:
    if mate_in is not None:
        sign = "+" if mate_in > 0 else ""
        return f"M{sign}{mate_in}"
    if cp is None:
        return "?"
    # Convert cp to pawns with sign and 2 decimals
    return f"{cp/100.0:+.2f}"


def main():
    ap = argparse.ArgumentParser(description="Analyze a chess game's moves with Stockfish and rate each move.")
    ap.add_argument("file", help="Path to a PGN file or a log containing a PGN section")
    ap.add_argument("--engine", default="stockfish", help="Path to stockfish executable (default: stockfish)")
    # Exactly one of time or depth may be provided; default to time
    ap.add_argument("--time", type=float, default=4, help="Analysis time per evaluation in seconds (default: 0.2)")
    ap.add_argument("--depth", type=int, default=None, help="Fixed depth per evaluation (overrides --time)")
    args = ap.parse_args()

    if not os.path.isfile(args.file):
        print(f"Input not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    with open(args.file, "r", encoding="utf-8", errors="replace") as f:
        raw = f.read()

    pgn_text = extract_pgn_text(raw)
    if not pgn_text:
        print("Could not locate PGN text in the file.", file=sys.stderr)
        sys.exit(2)

    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if game is None:
        print("Failed to parse PGN.", file=sys.stderr)
        sys.exit(3)

    # Prepare engine
    try:
        engine = chess.engine.SimpleEngine.popen_uci([args.engine])
    except FileNotFoundError:
        print(f"Could not launch engine at: {args.engine}", file=sys.stderr)
        print("Ensure Stockfish is installed and in PATH, or specify with --engine.", file=sys.stderr)
        sys.exit(4)

    limit: chess.engine.Limit
    if args.depth is not None:
        limit = chess.engine.Limit(depth=args.depth)
    else:
        limit = chess.engine.Limit(time=max(0.05, args.time))

    board = game.board()
    print("Game:")
    white = game.headers.get("White", "White")
    black = game.headers.get("Black", "Black")
    result = game.headers.get("Result", "*")
    print(f"  {white} vs {black}  Result: {result}")
    print()
    print("Columns: ply  side  move  played_eval  best_eval  loss  class  best_suggestion")

    ply = 1
    try:
        node = game
        while node.variations:
            move_node = node.variations[0]
            move = move_node.move
            mover_white = board.turn

            # Analyse position to get engine best move suggestion
            info_root_raw = engine.analyse(board, limit=limit, multipv=1)
            info_root = info_root_raw[0] if isinstance(info_root_raw, list) else info_root_raw
            best_move = None
            if info_root is not None and "pv" in info_root and info_root["pv"]:
                best_move = info_root["pv"][0]
            # Fallback to engine.play if PV missing
            if best_move is None:
                res = engine.play(board, limit)
                best_move = res.move

            # Evaluate played move position (for mover POV) using a temp board
            san = board.san(move)
            board_played = board.copy()
            board_played.push(move)
            info_played_raw = engine.analyse(board_played, limit=limit, multipv=1)
            info_played = info_played_raw[0] if isinstance(info_played_raw, list) else info_played_raw
            if info_played is None or "score" not in info_played:
                played_cp, played_mate = None, None
            else:
                played_cp, played_mate = score_to_cp(info_played["score"], pov_white=mover_white)

            # Evaluate best move position (for mover POV)
            best_san = board.san(best_move) if best_move is not None else "?"
            if best_move is not None:
                board_best = board.copy()
                board_best.push(best_move)
                info_best_raw = engine.analyse(board_best, limit=limit, multipv=1)
                info_best = info_best_raw[0] if isinstance(info_best_raw, list) else info_best_raw
                if info_best is None or "score" not in info_best:
                    best_cp, best_mate = None, None
                else:
                    best_cp, best_mate = score_to_cp(info_best["score"], pov_white=mover_white)
            else:
                best_cp, best_mate = None, None

            # Compute centipawn loss bands
            cp_loss: Optional[int] = None
            classification = "Unknown"
            # Handle mate cases first
            if best_mate is not None or played_mate is not None:
                if best_mate is not None and played_mate is not None:
                    # Same sign -> compare speed
                    if (best_mate > 0) and (played_mate > 0):
                        # Keeping a mate: equal speed Best; slower -> Inaccuracy; faster -> Best
                        if abs(played_mate) == abs(best_mate):
                            classification = "Best"
                        elif abs(played_mate) > abs(best_mate):
                            classification = "Inaccuracy"
                        else:
                            classification = "Best"
                    elif (best_mate < 0) and (played_mate < 0):
                        # Defending: equal delay Best; if played is sooner mate -> Blunder; if played delays more -> Good
                        if abs(played_mate) == abs(best_mate):
                            classification = "Best"
                        elif abs(played_mate) < abs(best_mate):
                            classification = "Blunder"
                        else:
                            classification = "Good"
                    else:
                        # Sign flip across who mates -> Blunder
                        classification = "Blunder"
                else:
                    # Losing a forced mate or missing one
                    classification = "Blunder"
            else:
                if best_cp is not None and played_cp is not None:
                    cp_loss = max(0, best_cp - played_cp)
                    classification = classify_cp_loss(cp_loss)

            side = "W" if mover_white else "B"
            print(
                f"{ply:>3}  {side}   {san:<8}  {fmt_eval(played_cp, played_mate):>10}  "
                f"{fmt_eval(best_cp, best_mate):>9}  "
                f"{(str(cp_loss) if cp_loss is not None else '—'):>5}  {classification:<12}  {best_san}"
            )

            node = move_node
            ply += 1
            # Advance the live board for the next ply
            board.push(move)
    finally:
        engine.quit()


if __name__ == "__main__":
    main()
