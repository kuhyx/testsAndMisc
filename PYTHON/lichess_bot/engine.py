import time
import random
from typing import Optional, Tuple

import chess


class RandomEngine:
    """A simple engine with a tiny alpha-beta search and material+mobility eval.

    Keeps the same name for compatibility, but no longer picks purely random moves.
    """

    def __init__(self, depth: int = 100, max_time_sec: float = 5):
        self.depth = depth
        self.max_time_sec = max_time_sec

        # Centipawn values
        self.piece_values = {
            chess.PAWN: 100,
            chess.KNIGHT: 320,
            chess.BISHOP: 330,
            chess.ROOK: 500,
            chess.QUEEN: 900,
            chess.KING: 0,
        }

    def choose_move(self, board: chess.Board) -> Optional[chess.Move]:
        start = time.time()
        best_move: Optional[chess.Move] = None
        best_score = -float("inf") if board.turn else float("inf")

        # Iterative deepening up to depth or time limit
        for d in range(1, self.depth + 1):
            elapsed = time.time() - start
            if elapsed >= self.max_time_sec:
                break
            score, move = self._search_root(board, d, start)
            if move is not None:
                best_move, best_score = move, score

        # Fallback to random if search didn’t find anything
        if best_move is None:
            moves = list(board.legal_moves)
            return random.choice(moves) if moves else None
        return best_move

    def choose_move_with_explanation(self, board: chess.Board) -> Tuple[Optional[chess.Move], str]:
        """Return the chosen move and a human-readable explanation of top candidates.

        The explanation lists top candidates with scores and quick annotations.
        """
        start = time.time()
        depth_used = 0
        best_move: Optional[chess.Move] = None
        scores: list[Tuple[chess.Move, float]] = []

        # Analyze all legal moves at the root with alpha-beta to given depth/time
        for d in range(1, self.depth + 1):
            if time.time() - start >= self.max_time_sec:
                break
            depth_used = d
            scores = self._analyze_root(board, d, start)
            if scores:
                best_move = scores[0][0]

        if not scores:
            # Fallback
            mv = self.choose_move(board)
            return mv, "fallback: random/legal-only (no analysis)"

        # Build explanation
        def annotate(m: chess.Move) -> str:
            tags = []
            if board.is_capture(m):
                tags.append("x")
            if m.promotion:
                tags.append(f"={chess.piece_symbol(m.promotion).upper()}")
            try:
                if board.gives_check(m):
                    tags.append("+")
            except Exception:
                pass
            return "".join(tags)

        top = scores[:5]
        best_cp = top[0][1]
        lines = [
            f"depth={depth_used} time={time.time()-start:.2f}s candidates={len(scores)}",
            f"best {board.san(top[0][0])} ({top[0][0].uci()}) score={best_cp:.1f}",
        ]
        if len(top) > 1:
            lines.append("alternatives:")
            for mv, sc in top[1:]:
                delta = sc - best_cp
                lines.append(f"  {board.san(mv)} ({mv.uci()}) score={sc:.1f} delta={delta:+.1f} {annotate(mv)}")

        return best_move, "\n".join(lines)

    def _analyze_root(self, board: chess.Board, depth: int, start: float) -> list[Tuple[chess.Move, float]]:
        alpha = -float("inf")
        beta = float("inf")
        scored: list[Tuple[chess.Move, float]] = []
        for move in self._ordered_moves(board):
            if time.time() - start >= self.max_time_sec:
                break
            board.push(move)
            score = -self._alphabeta(board, depth - 1, -beta, -alpha, start)
            board.pop()
            scored.append((move, score))
            if score > alpha:
                alpha = score
            if alpha >= beta:
                break
        scored.sort(key=lambda t: t[1], reverse=True)
        return scored

    def _search_root(self, board: chess.Board, depth: int, start: float) -> Tuple[float, Optional[chess.Move]]:
        alpha = -float("inf")
        beta = float("inf")
        best_move: Optional[chess.Move] = None
        best_score = -float("inf")

        moves = self._ordered_moves(board)
        for move in moves:
            if time.time() - start >= self.max_time_sec:
                break
            board.push(move)
            score = -self._alphabeta(board, depth - 1, -beta, -alpha, start)
            board.pop()
            if score > best_score:
                best_score = score
                best_move = move
            if score > alpha:
                alpha = score
            if alpha >= beta:
                break
        return best_score, best_move

    def _alphabeta(self, board: chess.Board, depth: int, alpha: float, beta: float, start: float) -> float:
        # Time cutoff
        if time.time() - start >= self.max_time_sec:
            return self._evaluate(board)

        # Terminal nodes
        if depth == 0 or board.is_game_over():
            return self._evaluate(board)

        best = -float("inf")
        for move in self._ordered_moves(board):
            board.push(move)
            score = -self._alphabeta(board, depth - 1, -beta, -alpha, start)
            board.pop()
            if score > best:
                best = score
            if best > alpha:
                alpha = best
            if alpha >= beta:
                break
        return best

    def _ordered_moves(self, board: chess.Board):
        # Simple move ordering: captures/promotions first, then checks
        def score_move(m: chess.Move) -> int:
            s = 0
            if board.is_capture(m):
                s += 1000
            if m.promotion:
                s += 800
            try:
                if board.gives_check(m):
                    s += 100
            except Exception:
                pass
            return s

        moves = list(board.legal_moves)
        moves.sort(key=score_move, reverse=True)
        return moves

    def _evaluate(self, board: chess.Board) -> float:
        # Game end conditions
        if board.is_checkmate():
            return -100000 if board.turn else 100000  # side-to-move is mated
        if board.is_stalemate() or board.is_insufficient_material() or board.can_claim_draw():
            return 0

        # Material
        material = 0
        for square, piece in board.piece_map().items():
            val = self.piece_values[piece.piece_type]
            material += val if piece.color == chess.WHITE else -val

        # Mobility (only side to move for speed; acts as tempo bonus)
        mobility = 5 * sum(1 for _ in board.legal_moves)
        if board.turn:
            mobility_term = mobility
        else:
            mobility_term = -mobility

        return material + mobility_term
