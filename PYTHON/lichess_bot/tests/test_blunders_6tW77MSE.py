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
    ("r2q1rk1/ppp1pp1p/6p1/2Pp3P/PP1nnPb1/8/8/RNB1KB1R w KQ - 0 13", "h5g6", "ply25_W_h5g6"),
    ("r2q1rk1/ppp1pp1p/6P1/2Pp4/PP1nnPb1/8/8/RNB1KB1R b KQ - 0 13", "f7g6", "ply26_B_f7g6"),
    ("r2q1rk1/ppp1p2p/6p1/2Pp4/PP1nnPb1/8/8/RNB1KB1R w KQ - 0 14", "c5c6", "ply27_W_c5c6"),
    ("r2q1rk1/ppp1p2p/2P3p1/3p4/PP1nnPb1/8/8/RNB1KB1R b KQ - 0 14", "g4f3", "ply28_B_g4f3"),
    ("r2q1rk1/ppp1p2p/2P3p1/3p4/PP1nnP2/5b2/8/RNB1KB1R w KQ - 1 15", "c6b7", "ply29_W_c6b7"),
    ("r2q1rk1/pPp1p2p/6p1/3p4/PP1nnP2/5b2/8/RNB1KB1R b KQ - 0 15", "a8b8", "ply30_B_a8b8"),
    ("1r1q1rk1/pPp1p2p/6p1/3p4/PP1nnP2/5b2/8/RNB1KB1R w KQ - 1 16", "f4f5", "ply31_W_f4f5"),
    ("1r1q1rk1/pPp1p2p/6p1/3p1P2/PP1nn3/5b2/8/RNB1KB1R b KQ - 0 16", "f3h1", "ply32_B_f3h1"),
    ("1r1q1rk1/pPp1p2p/6p1/3p1P2/PP1nn3/8/8/RNB1KB1b w Q - 0 17", "f5g6", "ply33_W_f5g6"),
    ("1r1q1rk1/pPp1p3/6p1/3p4/PP1nn3/8/8/RNB1KB1b w Q - 0 18", "b4b5", "ply35_W_b4b5"),
    ("1r1q1rk1/pPp1p3/6p1/1P1p4/P3n3/5n2/8/RNB1KB1b w Q - 1 19", "e1e2", "ply37_W_e1e2"),
    ("1r1q1rk1/pPp1p3/6p1/1P1p4/P3n3/5n2/4K3/RNB2B1b b - - 2 19", "e4g3", "ply38_B_e4g3"),
    ("1r1q1rk1/pPp1p3/6p1/1P1p4/P7/5nn1/4K3/RNB2B1b w - - 3 20", "e2e3", "ply39_W_e2e3"),
    ("1r1q1rk1/pPp1p3/6p1/1P1p4/P7/3K4/8/RNB1nn1b w - - 2 22", "d3d4", "ply43_W_d3d4"),
    ("1r1q2k1/pPp1p3/6p1/1P1p4/P2K1r2/8/8/RNB1nn1b w - - 4 23", "d4e5", "ply45_W_d4e5"),
    ("1r1q2k1/pPp1p3/6p1/1P1pK3/P4r2/8/8/RNB1nn1b b - - 5 23", "d8d6", "ply46_B_d8d6"),
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
