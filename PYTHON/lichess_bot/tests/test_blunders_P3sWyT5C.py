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
    ("r1bqk2r/ppp2ppp/2np1n2/2b1p3/2BPP3/2P2N2/PP3PPP/RNBQ1RK1 b kq - 0 6", "e8g8", "ply12_B_e8g8"),
    ("r1bq1r1k/ppP2ppp/2n2n2/4p1B1/2B1P3/1NP2N2/PP3PPP/R2Q1RK1 b - - 0 12", "h8g8", "ply24_B_h8g8"),
    ("r1bR2k1/pp3ppp/2n2n2/4p1B1/2B1P3/1NP2N2/PPQ2PPP/5RK1 b - - 0 16", "f6e8", "ply32_B_f6e8"),
    ("r1bRn1k1/pp3ppp/2n5/4p1B1/2B1P3/1NP2N2/PPQ2PPP/5RK1 w - - 1 17", "d8e8", "ply33_W_d8e8"),
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
