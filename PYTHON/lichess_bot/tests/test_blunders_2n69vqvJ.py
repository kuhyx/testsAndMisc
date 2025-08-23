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
    ("r1bqk2r/ppp2ppp/2np1n2/2b5/2BPP3/5N2/PP3PPP/RNBQ1RK1 b kq - 0 7", "f6e4", "ply14_B_f6e4"),
    ("r2qk2r/pppb2pp/2n5/2p3B1/Q1B1p3/5N2/PP3PPP/R4RK1 b kq - 1 12", "e4f3", "ply24_B_e4f3"),
    ("r2Bk2r/pppb2pp/2n5/2p5/Q1B5/8/PP3PpP/R4RK1 w kq - 0 14", "g1g2", "ply27_W_g1g2"),
    ("r1k4r/pppb2pp/2n5/2p5/2B5/1Q6/PP3PKP/3R1R2 b - - 3 16", "g7g6", "ply32_B_g7g6"),
    ("rk5r/ppp4p/2n2Qp1/2p5/8/8/PP3PKP/3R1R2 b - - 2 19", "b7b5", "ply38_B_b7b5"),
    ("rk5r/p1p4p/2n2Qp1/1pp5/8/8/PP3PKP/3R1R2 w - - 0 20", "f6h8", "ply39_W_f6h8"),
    ("r7/1kp4p/2n2Qp1/ppp5/8/8/PP3PKP/3R1R2 w - - 0 22", "d1d6", "ply43_W_d1d6"),
    ("8/8/2k3pR/1p6/p1p5/8/PP3PKP/8 b - - 1 29", "c6d7", "ply58_B_c6d7"),
    ("4k3/8/6R1/1p6/p1p5/8/PP3PKP/8 w - - 1 31", "f2f4", "ply61_W_f2f4"),
    ("4k3/8/6R1/1p3P2/p1p5/8/PP4KP/8 w - - 1 33", "f5f6", "ply65_W_f5f6"),
    ("4k3/8/5PR1/1p6/p1p5/8/PP4KP/8 b - - 0 33", "e8d8", "ply66_B_e8d8"),
    ("5k2/5P1R/8/1p6/p1p4P/8/PP4K1/8 w - - 1 38", "h4h5", "ply75_W_h4h5"),
    ("5k2/5P1R/8/1p5P/p1p5/8/PP4K1/8 b - - 0 38", "f8e7", "ply76_B_f8e7"),
    ("5k2/5PR1/7P/1p6/p1p5/8/PP4K1/8 b - - 2 40", "c4c3", "ply80_B_c4c3"),
    ("5k2/5PR1/7P/1p6/p7/2P5/P5K1/8 b - - 0 41", "f8e7", "ply82_B_f8e7"),
    ("5Q2/6R1/8/1p1k3Q/p7/2P5/P5K1/8 b - - 2 45", "d5e6", "ply90_B_d5e6"),
    ("5Q2/6R1/4k3/1p5Q/p7/2P5/P5K1/8 w - - 3 46", "g7g6", "ply91_W_g7g6"),
    ("5Q2/3k4/6R1/1p5Q/p7/2P5/P5K1/8 w - - 5 47", "f8f7", "ply93_W_f8f7"),
    ("3k4/5Q2/6R1/1p5Q/p7/2P5/P5K1/8 w - - 7 48", "h5h8", "ply95_W_h5h8"),
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
