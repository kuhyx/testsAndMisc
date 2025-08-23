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
    ("rnb2rk1/pp2bppp/8/8/2qN4/2N5/PPP2PPP/R1BQK2R w - - 3 13", "b2b3", "ply25_W_b2b3"),
    ("rn3rk1/pp2bppp/8/3Q1b2/8/1P6/2q2PPP/2B2K1R w - - 0 18", "d5b7", "ply35_W_d5b7"),
    ("rn3rk1/pQ2bppp/8/5b2/8/1P6/2q2PPP/2B2K1R b - - 0 18", "c2f2", "ply36_B_c2f2"),
    ("6k1/p2n1ppp/8/2b5/6b1/1P6/3K3P/4R3 b - - 0 27", "c5b4", "ply54_B_c5b4"),
    ("6k1/p2n1ppp/8/8/5Kb1/1P6/7P/4b3 b - - 1 29", "e1c3", "ply58_B_e1c3"),
    ("6k1/p2n1ppp/8/8/6K1/1Pb5/7P/8 b - - 0 30", "d7f6", "ply60_B_d7f6"),
    ("6k1/p4ppp/5n2/5K2/8/1Pb5/7P/8 b - - 2 31", "f6d7", "ply62_B_f6d7"),
    ("6k1/p2n1ppp/8/5K2/8/1Pb5/7P/8 w - - 3 32", "f5e4", "ply63_W_f5e4"),
    ("6k1/p2n1ppp/8/8/4K3/1Pb5/7P/8 b - - 4 32", "d7f6", "ply64_B_d7f6"),
    ("6k1/p4ppp/8/4b2n/4K3/1P5P/8/8 b - - 2 35", "e5b8", "ply70_B_e5b8"),
    ("1b4k1/p4ppp/8/7n/4K3/1P5P/8/8 w - - 3 36", "e4f5", "ply71_W_e4f5"),
    ("1b4k1/p4ppp/8/5K1n/8/1P5P/8/8 b - - 4 36", "b8d6", "ply72_B_b8d6"),
    ("6k1/p4ppp/3b4/5K1n/8/1P5P/8/8 w - - 5 37", "f5g5", "ply73_W_f5g5"),
    ("6k1/p4ppp/3b4/6Kn/8/1P5P/8/8 b - - 6 37", "h5f4", "ply74_B_h5f4"),
    ("6k1/p4ppp/3b4/8/5nK1/1P5P/8/8 b - - 8 38", "h7h5", "ply76_B_h7h5"),
    ("6k1/p4pp1/3b4/7p/5nK1/1P5P/8/8 w - - 0 39", "g4g3", "ply77_W_g4g3"),
    ("6k1/p4pp1/3b4/7p/5n2/1P4KP/8/8 b - - 1 39", "f4e6", "ply78_B_f4e6"),
    ("6k1/p4pp1/3bn3/7p/8/1P4KP/8/8 w - - 2 40", "g3h4", "ply79_W_g3h4"),
    ("6k1/p4pp1/3bn3/7p/7K/1P5P/8/8 b - - 3 40", "e6c5", "ply80_B_e6c5"),
    ("6k1/p4pp1/3b4/2n4p/7K/1P5P/8/8 w - - 4 41", "h4h5", "ply81_W_h4h5"),
    ("6k1/p4pp1/3b4/2n4K/8/1P5P/8/8 b - - 0 41", "c5b3", "ply82_B_c5b3"),
    ("6k1/p4pp1/3b4/6K1/8/1n5P/8/8 b - - 1 42", "d6e7", "ply84_B_d6e7"),
    ("6k1/p3bpp1/8/5K2/8/1n5P/8/8 b - - 3 43", "b3d4", "ply86_B_b3d4"),
    ("8/p3kpp1/5b2/8/3nK3/7P/8/8 w - - 10 47", "e4f4", "ply93_W_e4f4"),
    ("8/p3kpp1/4nb2/8/5K2/7P/8/8 w - - 12 48", "f4f5", "ply95_W_f4f5"),
    ("6k1/p4pp1/5b2/3K4/3n4/7P/8/8 w - - 18 51", "d5d6", "ply101_W_d5d6"),
    ("6k1/p4pp1/4nb2/2K5/8/7P/8/8 w - - 24 54", "c5d6", "ply107_W_c5d6"),
    ("6k1/p4pp1/3K1b2/8/5n2/7P/8/8 w - - 26 55", "d6d7", "ply109_W_d6d7"),
    ("6k1/p2K1pp1/5b2/8/8/7n/8/8 w - - 0 56", "d7e8", "ply111_W_d7e8"),
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
