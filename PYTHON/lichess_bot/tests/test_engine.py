import chess
from PYTHON.lichess_bot.engine import RandomEngine


def test_random_engine_returns_move_on_start_position():
    board = chess.Board()
    eng = RandomEngine()
    move = eng.choose_move(board)
    assert move is not None
    assert move in board.legal_moves
