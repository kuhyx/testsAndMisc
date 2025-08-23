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
    ("r1bqk2r/ppp2ppp/2np1n2/2b1p3/2BPP3/2P2N2/PP3PPP/RNBQ1RK1 b kq - 0 6", "h7h5", "ply12_B_h7h5"),
    ("r1br3k/5B2/2n2n2/pp2p1Bp/4P3/1QP2N2/PP3PPP/RN3RK1 b - - 0 13", "h5h4", "ply26_B_h5h4"),
    ("r1br4/5B1k/2n2B2/pp2p3/4P2p/1QP2N2/PP3PPP/RN3RK1 w - - 1 15", "f6d8", "ply29_W_f6d8"),
    ("r1bB4/5B1k/2n5/pp2p3/4P2p/1QP2N2/PP3PPP/RN3RK1 b - - 0 15", "b5b4", "ply30_B_b5b4"),
    ("r1bB4/5B1k/2n5/p3p3/1p2P2p/1QP2N2/PP3PPP/RN3RK1 w - - 0 16", "f7d5", "ply31_W_f7d5"),
    ("r1bB4/7k/2n5/p2Bp3/1p2P2p/1QP2N2/PP3PPP/RN3RK1 b - - 1 16", "b4c3", "ply32_B_b4c3"),
    ("r1bB4/7k/2B5/p3p3/4P2p/1Qp2N2/PP3PPP/RN3RK1 b - - 0 17", "c3c2", "ply34_B_c3c2"),
    ("B1bB4/7k/8/p3p3/4P2p/1Q3N2/PPp2PPP/RN3RK1 b - - 0 18", "c2b1q", "ply36_B_c2b1q"),
    ("B1bB4/7k/8/p3p3/4P2p/1Q3N2/PP3PPP/1R3RK1 b - - 0 19", "a5a4", "ply38_B_a5a4"),
    ("B1bB4/5Q2/7k/4p3/p3P2p/5N2/PP3PPP/1R3RK1 w - - 2 21", "d8g5", "ply41_W_d8g5"),
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
