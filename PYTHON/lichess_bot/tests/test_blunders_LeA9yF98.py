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
    ("r1bqk2r/ppp2ppp/2np1n2/2b1p3/2BPP3/2P2N2/PP3PPP/RNBQ1RK1 b kq - 0 6", "d6d5", "ply12_B_d6d5"),
    ("r1bqk2r/ppp2ppp/2n2n2/2bpp3/2BPP3/2P2N2/PP3PPP/RNBQ1RK1 w kq - 0 7", "d4c5", "ply13_W_d4c5"),
    ("r1bqk2r/ppp2ppp/2n2n2/2Ppp3/2B1P3/2P2N2/PP3PPP/RNBQ1RK1 b kq - 0 7", "d5e4", "ply14_B_d5e4"),
    ("r1bB2kr/2p2p2/p1B5/2P3pp/1Pp1p3/4P3/P2N2PP/RN1Q1RK1 b - - 0 17", "g8h7", "ply34_B_g8h7"),
    ("B1bB3r/2p2p1k/p7/2P3pp/1Pp1p3/4P3/P2N2PP/RN1Q1RK1 b - - 0 18", "h7g7", "ply36_B_h7g7"),
    ("B1b4r/2p2pk1/p4B2/2P3pp/1Pp1p3/4P3/P2N2PP/RN1Q1RK1 b - - 2 19", "g7g8", "ply38_B_g7g8"),
    ("B1b3kB/2p2p2/p7/2P3pp/1Pp1p3/4P3/P2N2PP/RN1Q1RK1 b - - 0 20", "g8f8", "ply40_B_g8f8"),
    ("B1b2k1B/2p2p2/p7/2P3pQ/1Pp1p3/4P3/P2N2PP/RN3RK1 b - - 0 21", "f8e8", "ply42_B_f8e8"),
    ("B1b1k2B/2p2R2/p7/2P3pQ/1Pp1p3/4P3/P2N2PP/RN4K1 b - - 0 22", "c7c6", "ply44_B_c7c6"),
    ("5k1B/3R4/p1B5/2P3pQ/1Pp1p3/4P3/P2N2PP/RN4K1 w - - 1 25", "d7d8", "ply49_W_d7d8"),
    ("3R3B/4k3/p1B5/2P3pQ/1Pp1p3/4P3/P2N2PP/RN4K1 w - - 3 26", "h5e8", "ply51_W_h5e8"),
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
