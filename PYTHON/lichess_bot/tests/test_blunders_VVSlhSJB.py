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
    ("r1bqk2r/ppp2ppp/2np1n2/2b1p1B1/2B1P3/3P1N2/PPP2PPP/RN1Q1RK1 b kq - 1 6", "c5f2", "ply12_B_c5f2"),
    ("r1bq1rk1/pp3ppp/3p1n2/2p1p1B1/2P1P3/2PP1N2/P5PP/RN1Q1RK1 b - - 0 11", "f6e4", "ply22_B_f6e4"),
    ("3r1r2/pp3ppk/3N3p/2p1N3/4P3/2P5/P5PP/R2Q1RK1 b - - 0 17", "h7g8", "ply34_B_h7g8"),
    ("3r1rk1/pp3pp1/3N3p/2p1N3/4P3/2P5/P5PP/R2Q1RK1 w - - 1 18", "e5f7", "ply35_W_e5f7"),
    ("3r1rk1/pp3Np1/3N3p/2p5/4P3/2P5/P5PP/R2Q1RK1 b - - 0 18", "f8f7", "ply36_B_f8f7"),
    ("5Q2/p5pk/4P2p/1pp5/8/2P5/P5PP/5RK1 b - - 0 24", "h7g6", "ply48_B_h7g6"),
    ("5Q2/p5p1/4P1kp/1pp5/8/2P5/P5PP/5RK1 w - - 1 25", "e6e7", "ply49_W_e6e7"),
    ("5Q2/p3P1p1/6kp/1pp5/8/2P5/P5PP/5RK1 b - - 0 25", "g6h7", "ply50_B_g6h7"),
    ("4QQ2/p6k/6pp/1pp5/8/2P5/P5PP/5RK1 w - - 0 27", "f8h8", "ply53_W_f8h8"),
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
