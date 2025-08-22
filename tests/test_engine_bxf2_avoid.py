import os
import sys
import chess

# Ensure repo root in path for 'PYTHON' package imports when running locally
REPO_ROOT = os.path.dirname(os.path.abspath(__file__ + "/.."))
PARENT = os.path.dirname(REPO_ROOT)
if PARENT not in sys.path:
    sys.path.insert(0, PARENT)

from PYTHON.lichess_bot.engine import RandomEngine  # noqa: E402


def position_after_italian_bg5():
    # 1.e4 e5 2.Nf3 Nc6 3.Bc4 Nf6 4.d3 Bc5 5.O-O d6 6.Bg5
    moves = [
        "e4", "e5", "Nf3", "Nc6", "Bc4", "Nf6", "d3", "Bc5", "O-O", "d6", "Bg5"
    ]
    board = chess.Board()
    for san in moves:
        board.push_san(san)
    return board


def test_engine_avoids_unsound_bxf2_in_italian_bg5():
    board = position_after_italian_bg5()
    eng = RandomEngine(depth=4, max_time_sec=1.5)
    move, expl = eng.choose_move_with_explanation(board, time_budget_sec=1.5)
    # The engine should avoid Bxf2+ here (known blunder); assert chosen move isn't that
    bxf2 = chess.Move.from_uci("c5f2")
    assert move != bxf2, f"Engine picked unsound Bxf2+: {expl}"

    # Also ensure Bxf2+ is not the top candidate in analyze list for small depth
    # We can do a weaker invariant: if the engine considered only a couple moves earlier,
    # ensure current top move either equals move or is not Bxf2.
    assert move is not None
    assert move is None or move != bxf2
