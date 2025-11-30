import csv
import os

import chess
import pytest

from PYTHON.lichess_bot.engine import RandomEngine


def _load_top_puzzles(csv_path: str, limit: int = 8) -> list[tuple[str, str]]:
    """Return a list of (FEN, solution_moves_str) for the first `limit` rows in the CSV.
    CSV columns: PuzzleId,FEN,Moves,...
    """
    puzzles: list[tuple[str, str]] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            fen = row["FEN"].strip()
            moves = row["Moves"].strip()
            if fen and moves:
                puzzles.append((fen, moves))
            if len(puzzles) >= limit:
                break
    return puzzles


@pytest.mark.parametrize(
    ("fen", "moves_str"),
    _load_top_puzzles(
        os.path.join(os.path.dirname(__file__), "lichess_db_puzzle.csv"), limit=8
    ),
)
def test_puzzle_engine_follow_solution(fen: str, moves_str: str):
    board = chess.Board(fen)
    eng = RandomEngine(max_time_sec=1.0)

    # Moves are space-separated UCIs alternating sides
    # starting from side-to-move in the FEN
    solution_moves = moves_str.split()
    step = 0
    for uci in solution_moves:
        step += 1
        # Engine move on this ply
        mv, expl = eng.choose_move_with_explanation(board, time_budget_sec=0.5)
        assert mv is not None, f"No move returned at step {step}.\nExplanation: {expl}"

        # If engine move differs from solution, fail immediately
        # but provide analysis of the correct move
        if mv.uci() != uci:
            # Ask the engine to analyze the correct move for debug
            score_cp, proposed_expl, best_mv, best_expl = (
                eng.evaluate_proposed_move_with_suggestion(
                    board, uci, time_budget_sec=0.5
                )
            )
            details = [
                f"Puzzle failed at step {step}.",
                f"FEN: {fen}",
                f"Expected: {uci}",
                f"Engine played: {mv.uci()}",
                "--- engine explanation ---",
                expl,
                "--- analysis of expected move ---",
                f"score_cp: {score_cp}",
                proposed_expl,
            ]
            if best_mv is not None:
                details.append("--- engine best move analysis ---")
                details.append(best_expl)
            pytest.fail("\n".join(details))

        # Apply the move and continue
        board.push(mv)
