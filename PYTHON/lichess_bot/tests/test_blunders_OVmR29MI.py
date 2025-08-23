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
    ("rnb1kb1r/pp3ppp/4q3/2p3N1/4p3/8/PPPPNPPP/R1BQ1RK1 b kq - 1 9", "e6a2", "ply18_B_e6a2"),
    ("2kr3r/1p4p1/4bp2/7p/Q2b1B2/2P5/1P3PPP/5RK1 w - - 0 20", "c3d4", "ply39_W_c3d4"),
    ("2kr3r/1p4p1/4bp2/7p/Q2P1B2/8/1P3PPP/5RK1 b - - 0 20", "e6d5", "ply40_B_e6d5"),
    ("2kr3r/1p4p1/5p2/3b3p/Q2P1B2/8/1P3PPP/5RK1 w - - 1 21", "a4a8", "ply41_W_a4a8"),
    ("3r3r/1p1k2p1/5p2/3b3p/Q2P1B2/8/1P3PPP/5RK1 b - - 4 22", "d7c8", "ply44_B_d7c8"),
    ("2kr3r/1p4p1/5p2/Q2b3p/3P1B2/8/1P3PPP/5RK1 b - - 6 23", "b7b6", "ply46_B_b7b6"),
    ("2kr3r/6p1/1Q3p2/3b3p/3P1B2/8/1P3PPP/5RK1 b - - 0 24", "c8d7", "ply48_B_c8d7"),
    ("3r3r/3k2p1/1Q3p2/3b3p/3P1B2/8/1P3PPP/5RK1 w - - 1 25", "f4c7", "ply49_W_f4c7"),
    ("3r3r/2Bk2p1/1Q3p2/3b3p/3P4/8/1P3PPP/5RK1 b - - 2 25", "d8c8", "ply50_B_d8c8"),
    ("2r4r/2Bk2p1/1Q3p2/3b3p/3P4/8/1P3PPP/5RK1 w - - 3 26", "c7b8", "ply51_W_c7b8"),
    ("1r5r/Q5p1/4kp2/3b3p/3P4/8/1P3PPP/4R1K1 b - - 3 28", "e6d6", "ply56_B_e6d6"),
    ("1r5r/2k1R1p1/5p2/3Q3p/3P4/8/1P3PPP/6K1 b - - 2 31", "c7c8", "ply62_B_c7c8"),
    ("1rk4r/4R1p1/5p2/3Q3p/3P4/8/1P3PPP/6K1 w - - 3 32", "d5c5", "ply63_W_d5c5"),
    ("1r1k3r/4R1p1/5p2/2Q4p/3P4/8/1P3PPP/6K1 w - - 5 33", "d4d5", "ply65_W_d4d5"),
    ("3k3r/1Q2R3/5pp1/3P3p/8/8/1P3PPP/6K1 w - - 0 37", "d5d6", "ply73_W_d5d6"),
    ("3k3r/1Q2R3/3P1p2/6pp/8/8/1P3PPP/6K1 w - - 0 38", "b7b8", "ply75_W_b7b8"),
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
