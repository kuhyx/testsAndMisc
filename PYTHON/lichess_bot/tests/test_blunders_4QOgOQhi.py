import os
import sys
import chess
import pytest

# Ensure repo root is importable when running pytest directly
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from PYTHON.lichess_bot.engine import RandomEngine  # noqa: E402

BLUNDER_CASES = [
    ("r4qk1/p1p4p/np4p1/3p1p2/3P4/3K1N2/PP3nPP/RN5R w - - 2 18", "d3c3", "ply35_W_d3c3"),
    ("r4qk1/p1p4p/np4p1/3p1p2/3P4/2K2N2/PP3nPP/RN5R b - - 3 18", "f2h1", "ply36_B_f2h1"),
    ("r4qk1/p1p4p/1p4p1/3p1p2/1n1P4/3K1N2/PP4PP/RN5n w - - 2 20", "d3e3", "ply39_W_d3e3"),
    ("r5k1/p1p1q2p/1p4p1/3p1p2/1n1P4/4KN2/PP4PP/RN5n w - - 4 21", "e3f4", "ply41_W_e3f4"),
    ("r5k1/p1p1q2p/1p4p1/3p1p2/1n1P1K2/5N2/PP4PP/RN5n b - - 5 21", "e7e4", "ply42_B_e7e4"),
    ("r5k1/p1p4p/1p4p1/3p1pK1/1n1P2q1/5N2/PP4PP/RN5n w - - 8 23", "g5h6", "ply45_W_g5h6"),
    ("r5k1/p1p4p/1p4pK/3p1p2/1n1P2q1/5N2/PP4PP/RN5n b - - 9 23", "g4h5", "ply46_B_g4h5"),
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
