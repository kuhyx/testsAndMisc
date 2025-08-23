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
    ("r4r2/p2p3k/n2Np1p1/q1p5/P5Q1/8/3NKP2/8 b - - 2 24", "a5c7", "ply48_B_a5c7"),
    ("r4N2/p6k/n5pq/P1pp4/6Q1/5N2/4KP2/8 b - - 0 30", "h6f8", "ply60_B_h6f8"),
    ("r4q2/p6k/n5p1/P1pp4/6Q1/5N2/4KP2/8 w - - 0 31", "g4h3", "ply61_W_g4h3"),
    ("r4qk1/p2Q4/n5p1/P1pp4/8/5N2/4KP2/8 w - - 4 33", "e2e3", "ply65_W_e2e3"),
    ("4rqk1/p2Q4/n5p1/P1pp4/8/4KN2/5P2/8 w - - 6 34", "e3d2", "ply67_W_e3d2"),
    ("4rqk1/p2Q4/n5p1/P1pp4/8/5N2/3K1P2/8 b - - 7 34", "d5d4", "ply68_B_d5d4"),
    ("4rqk1/p2Q4/n5p1/P1p5/3p4/5N2/3K1P2/8 w - - 0 35", "d7a7", "ply69_W_d7a7"),
    ("4r1k1/Q7/n5p1/P1p5/3p4/5q2/3K1P2/8 w - - 0 36", "d2c2", "ply71_W_d2c2"),
    ("6k1/Q7/n5p1/P1p5/3p4/8/4rq2/3K4 w - - 0 38", "d1c1", "ply75_W_d1c1"),
    ("6k1/Q7/n5p1/P1p5/3p4/8/4rq2/2K5 b - - 1 38", "f2e1", "ply76_B_f2e1"),
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
