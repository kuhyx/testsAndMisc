import random
from typing import Optional

import chess


class RandomEngine:
    """Picks a random legal move.

    You can replace this with a UCI engine wrapper or a better search.
    """

    def choose_move(self, board: chess.Board) -> Optional[chess.Move]:
        moves = list(board.legal_moves)
        if not moves:
            return None
        return random.choice(moves)
