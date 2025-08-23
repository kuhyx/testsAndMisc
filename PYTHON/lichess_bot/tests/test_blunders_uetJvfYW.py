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
    ("rnbqkb1r/pppppppp/8/4P3/5n2/2NP4/PPP2PPP/R1BQKBNR b KQkq - 0 4", "g7g6", "ply8_B_g7g6"),
    ("rnbqkb1r/pppppp1p/6p1/4P3/5n2/2NP4/PPP2PPP/R1BQKBNR w KQkq - 0 5", "g1f3", "ply9_W_g1f3"),
    ("rnbqkb1r/pppppp1p/6p1/4P3/5n2/2NP1N2/PPP2PPP/R1BQKB1R b KQkq - 1 5", "f8g7", "ply10_B_f8g7"),
    ("rnbq1rk1/3p1pbp/p1p3p1/3pP3/Pp3BPP/2N2N2/1PP2P2/R2QKB1R w KQ - 0 13", "b2b3", "ply25_W_b2b3"),
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
