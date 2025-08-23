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
    ("1r1q1r2/pPp1pp1k/5P2/3p4/P7/1b6/8/bNB1KB1n b - - 0 18", "a1c3", "ply36_B_a1c3"),
    ("1r1q1r2/pPp1pp1k/5P2/3p4/P7/1bb5/8/1NB1KB1n w - - 1 19", "b1d2", "ply37_W_b1d2"),
    ("1r1q1r2/pPp1pp1k/5P2/3p4/P7/1bb5/3N4/2B1KB1n b - - 2 19", "c3d2", "ply38_B_c3d2"),
    ("1r1q1r2/pPp1pp1k/5P2/3p4/P7/1b6/3b4/2B1KB1n w - - 0 20", "c1d2", "ply39_W_c1d2"),
    ("1r1q1r2/pPp1pp1k/5P2/3p4/P7/1b6/3B4/4KB1n b - - 0 20", "h1g3", "ply40_B_h1g3"),
    ("1r1q1r2/pPp1pp1k/5P2/3p4/P7/1b4n1/3B4/4KB2 w - - 1 21", "f6e7", "ply41_W_f6e7"),
    ("1r3r2/pPp1qp1k/8/3p4/P7/1b4n1/3B4/4KB2 w - - 0 22", "f1e2", "ply43_W_f1e2"),
    ("1r3r2/pPp1qp1k/8/3p4/P7/1b4n1/3BB3/4K3 b - - 1 22", "e7e3", "ply44_B_e7e3"),
    ("1r3r2/pPp2p1k/8/3p4/P7/1b2q1n1/3BB3/4K3 w - - 2 23", "a4a5", "ply45_W_a4a5"),
    ("1r3r2/pPp2p1k/8/P2p4/8/1b2q1n1/3BB3/4K3 b - - 0 23", "e3e2", "ply46_B_e3e2"),
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
