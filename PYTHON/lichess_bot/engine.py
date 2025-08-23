import time
import random
from typing import Optional, Tuple

import chess


class RandomEngine:
    """A simple engine with a tiny alpha-beta search and material+mobility eval.

    Keeps the same name for compatibility, but no longer picks purely random moves.
    """

    def __init__(self, depth: int = 100, max_time_sec: float = 20):
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

        # Tiny hand-crafted opening book (UCIs); used only for the first few plies
        # Keys are tuples of UCI moves played so far from the starting position
        self.opening_book: dict[tuple[str, ...], list[str]] = {
            # As White (start position)
            tuple(): ["e2e4", "d2d4", "c2c4", "g1f3"],
            # As Black after 1.e4
            ("e2e4",): ["e7e5", "c7c5", "e7e6", "c7c6", "g8f6", "d7d5"],
            # As Black after 1.d4
            ("d2d4",): ["d7d5", "g8f6", "e7e6", "c7c5", "c7c6"],
            # As Black after 1.c4
            ("c2c4",): ["e7e5", "g8f6", "c7c5", "e7e6"],
            # As Black after 1.Nf3
            ("g1f3",): ["g8f6", "d7d5", "c7c5", "e7e6"],
            # A couple continuations to avoid silly early queen/rook moves
            ("e2e4", "e7e5"): ["g1f3", "f1c4", "f1b5", "d2d4"],
            ("e2e4", "c7c5"): ["g1f3", "d2d4", "c2c3", "b1c3"],
            ("d2d4", "d7d5"): ["c2c4", "g1f3", "e2e3"],
            ("d2d4", "g8f6"): ["c2c4", "g1f3", "e2e3"],

            # --- More specific continuations to steer sensible early play ---
            # 1.e4 e5 2.Nf3 (Black to move)
            ("e2e4", "e7e5", "g1f3"): ["b8c6", "g8f6", "f8c5", "d7d6"],
            # Italian: 1.e4 e5 2.Nf3 Nc6 3.Bc4 (Black to move)
            ("e2e4", "e7e5", "g1f3", "b8c6", "f1c4"): ["g8f6", "f8c5", "d7d6"],
            # Ruy Lopez: 1.e4 e5 2.Nf3 Nc6 3.Bb5 (Black to move)
            ("e2e4", "e7e5", "g1f3", "b8c6", "f1b5"): ["a7a6", "g8f6", "f8c5", "d7d6"],
            # Scotch: 1.e4 e5 2.Nf3 Nc6 3.d4 (Black to move)
            ("e2e4", "e7e5", "g1f3", "b8c6", "d2d4"): ["e5d4", "g8f6"],
            # Queen's Gambit: 1.d4 d5 2.c4 (Black to move)
            ("d2d4", "d7d5", "c2c4"): ["e7e6", "c7c6", "d5c4"],
            # English: 1.c4 e5 2.Nc3 (Black to move)
            ("c2c4", "e7e5", "b1c3"): ["g8f6", "b8c6"],
        }

    def choose_move(self, board: chess.Board, time_budget_sec: Optional[float] = None) -> Optional[chess.Move]:
        start = time.time()
        best_move: Optional[chess.Move] = None
        # Set a per-move deadline used throughout search
        time_limit = time_budget_sec if time_budget_sec is not None else self.max_time_sec
        self._deadline = start + max(0.01, time_limit)
        best_score = -float("inf") if board.turn else float("inf")

    # Opening book shortcut (very early only)
        book_mv = self._opening_book_move(board)
        if book_mv is not None:
            return book_mv

        # Iterative deepening up to depth or time limit
        for d in range(1, self.depth + 1):
            if time.time() >= self._deadline:
                break
            score, move = self._search_root(board, d, start)
            if move is not None:
                best_move, best_score = move, score

        # Fallback to random if search didn’t find anything
        if best_move is None:
            moves = list(board.legal_moves)
            return random.choice(moves) if moves else None
        return best_move

    def choose_move_with_explanation(self, board: chess.Board, time_budget_sec: Optional[float] = None) -> Tuple[Optional[chess.Move], str]:
        """Return the chosen move and a human-readable explanation of top candidates.

        The explanation lists top candidates with scores and quick annotations.
        """
        start = time.time()
        # Set a per-move deadline used throughout search
        time_limit = time_budget_sec if time_budget_sec is not None else self.max_time_sec
        self._deadline = start + max(0.01, time_limit)
        depth_used = 0
        best_move: Optional[chess.Move] = None
        scores: list[Tuple[chess.Move, float]] = []

        # Opening book shortcut
        book_mv = self._opening_book_move(board)
        if book_mv is not None:
            try:
                return book_mv, f"opening-book: {board.san(book_mv)} ({book_mv.uci()})"
            except Exception:
                return book_mv, f"opening-book: {book_mv.uci()}"

        # Analyze all legal moves at the root with alpha-beta to given depth/time
        for d in range(1, self.depth + 1):
            if time.time() >= self._deadline:
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
                tags.append("capture")
            if m.promotion:
                tags.append(f"promotes={chess.piece_symbol(m.promotion).upper()}")
            try:
                if board.gives_check(m):
                    tags.append("check")
            except Exception:
                pass
            if board.is_castling(m):
                tags.append("castle")
            # Centralization
            center = {chess.D4, chess.E4, chess.D5, chess.E5}
            if m.to_square in center:
                tags.append("center")
            # Development: minor piece leaves back rank
            if board.piece_at(m.from_square) and board.piece_at(m.from_square).piece_type in (chess.KNIGHT, chess.BISHOP):
                if chess.square_rank(m.from_square) in (0, 7):
                    tags.append("develops")
            # Rook to (semi-)open file
            if board.piece_at(m.from_square) and board.piece_at(m.from_square).piece_type == chess.ROOK:
                file_idx = chess.square_file(m.to_square)
                if self._is_open_file(board, file_idx):
                    tags.append("open-file")
            return ",".join(tags)

        top = scores[:5]
        best_cp = top[0][1]
        lines = [
            f"depth={depth_used} time={time.time()-start:.2f}s candidates={len(scores)}",
            f"best {board.san(top[0][0])} ({top[0][0].uci()}) score={best_cp:.1f} reasons=[{annotate(top[0][0])}]",
        ]
        if len(top) > 1:
            lines.append("alternatives:")
            for mv, sc in top[1:]:
                delta = sc - best_cp
                lines.append(f"  {board.san(mv)} ({mv.uci()}) score={sc:.1f} delta={delta:+.1f} reasons=[{annotate(mv)}]")

        return best_move, "\n".join(lines)

    def _analyze_root(self, board: chess.Board, depth: int, start: float) -> list[Tuple[chess.Move, float]]:
        alpha = -float("inf")
        beta = float("inf")
        scored: list[Tuple[chess.Move, float]] = []
        for move in self._ordered_moves(board):
            if time.time() >= self._deadline:
                break
            board.push(move)
            score = -self._alphabeta(board, depth - 1, -beta, -alpha, start)
            board.pop()
            scored.append((move, score))
            if score > alpha:
                alpha = score
            if alpha >= beta:
                break
        # Prefer higher score; on ties, prefer lower risk
        risk_map = {m: self._risk_score(board, m) for m, _ in scored}
        scored.sort(key=lambda t: (t[1], -risk_map[t[0]]), reverse=True)
        return scored

    def _search_root(self, board: chess.Board, depth: int, start: float) -> Tuple[float, Optional[chess.Move]]:
        alpha = -float("inf")
        beta = float("inf")
        best_move: Optional[chess.Move] = None
        best_score = -float("inf")

        moves = self._ordered_moves(board)
        for move in moves:
            if time.time() >= self._deadline:
                break
            board.push(move)
            score = -self._alphabeta(board, depth - 1, -beta, -alpha, start)
            board.pop()
            # Prefer lower-risk choices on score ties
            if score > best_score:
                best_score = score
                best_move = move
            elif best_move is not None and (score == best_score or abs(score - best_score) < 1e-3):
                if self._risk_score(board, move) < self._risk_score(board, best_move):
                    best_move = move
            if score > alpha:
                alpha = score
            if alpha >= beta:
                break
        return best_score, best_move

    def _alphabeta(self, board: chess.Board, depth: int, alpha: float, beta: float, start: float) -> float:
        # Time cutoff
        if time.time() >= self._deadline:
            return self._evaluate(board)

        # Terminal nodes
        if board.is_game_over():
            return self._evaluate(board)
        if depth == 0:
            return self._quiescence(board, alpha, beta, start)

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

    def _quiescence(self, board: chess.Board, alpha: float, beta: float, start: float) -> float:
        # Stand-pat
        stand_pat = self._evaluate(board)
        if stand_pat >= beta:
            return beta
        if stand_pat > alpha:
            alpha = stand_pat

        # Explore captures to avoid horizon effect
        # Consider only captures/promotions and order by SEE to reduce blunders
        capture_moves: list[tuple[int, chess.Move]] = []
        for move in self._ordered_moves(board):
            if time.time() >= self._deadline:
                break
            if not board.is_capture(move) and not move.promotion:
                continue
            try:
                capture_moves.append((int(self._see_value(board, move)), move))
            except Exception:
                capture_moves.append((0, move))

        capture_moves.sort(key=lambda t: t[0], reverse=True)

        for _, move in capture_moves:
            if time.time() >= self._deadline:
                break
            board.push(move)
            score = -self._quiescence(board, -beta, -alpha, start)
            board.pop()
            if score >= beta:
                return beta
            if score > alpha:
                alpha = score
        return alpha

    def _ordered_moves(self, board: chess.Board):
        # Move ordering that mixes tactical SEE with simple heuristics
        def score_move(m: chess.Move) -> int:
            s = 0
            is_cap = board.is_capture(m)
            if is_cap:
                s += 1000
            if m.promotion:
                s += 800
            try:
                if board.gives_check(m):
                    s += 120
            except Exception:
                pass

            # SEE: reward good captures and avoid obviously losing moves
            try:
                see = int(self._see_value(board, m))
                if is_cap or see < 0:
                    s += max(-600, min(600, see))
            except Exception:
                pass

            early = self._is_early_game(board)
            piece = board.piece_at(m.from_square)
            if piece:
                # Heuristic: demote unsound early bishop sacs on f2/f7
                if early and self._is_bishop_sac_on_f2f7(board, m):
                    try:
                        see_sac = int(self._see_value(board, m))
                    except Exception:
                        see_sac = -300
                    # Large penalty if SEE is bad or not clearly winning material
                    if see_sac <= -50:
                        s -= 1300  # outweigh capture+check bonuses
                    else:
                        s -= 600
                # Discourage premature queen adventures in the opening
                if piece.piece_type == chess.QUEEN and early:
                    # Strongly demote greedy corner rook captures like Qxh8/Qxa8/Qxh1/Qxa1
                    if is_cap:
                        victim = board.piece_at(m.to_square)
                        if victim and victim.piece_type == chess.ROOK and m.to_square in {chess.A8, chess.H8, chess.A1, chess.H1}:
                            try:
                                if board.gives_check(m):
                                    s -= 1200
                                else:
                                    s -= 900
                            except Exception:
                                s -= 900
                    victim = board.piece_at(m.to_square)
                    # Penalize queen pawn-grabs on edge pawns (a2/b2/g2/h2 or a7/b7/g7/h7)
                    poison_targets_white = {chess.A7, chess.B7, chess.G7, chess.H7}
                    poison_targets_black = {chess.A2, chess.B2, chess.G2, chess.H2}
                    is_poison_target = (
                        (piece.color == chess.WHITE and m.to_square in poison_targets_white)
                        or (piece.color == chess.BLACK and m.to_square in poison_targets_black)
                    )
                    if is_cap and victim and victim.piece_type == chess.PAWN and is_poison_target:
                        # If destination is heavily attacked, apply a large penalty
                        attackers_op = len(board.attackers(not piece.color, m.to_square))
                        defenders_me = len(board.attackers(piece.color, m.to_square))
                        if attackers_op >= max(1, defenders_me):
                            s -= 500
                        else:
                            s -= 250
                    # General small penalty for non-check queen moves before minor development
                    if not is_cap:
                        if self._most_minors_undeveloped(board, piece.color):
                            s -= 160
                        else:
                            s -= 60
                if board.is_castling(m):
                    s += 650
                if piece.piece_type in (chess.KNIGHT, chess.BISHOP):
                    if chess.square_rank(m.from_square) in (0, 7) and not is_cap:
                        s += 90
                if early and piece.piece_type == chess.KNIGHT:
                    to_file = chess.square_file(m.to_square)
                    if to_file in (0, 7) and not is_cap:
                        s -= 140
                if piece.piece_type == chess.KING and early and not board.is_castling(m):
                    s -= 450
                if piece.piece_type == chess.ROOK and early and self._most_minors_undeveloped(board, piece.color):
                    s -= 140
                if piece.piece_type == chess.QUEEN and early and not is_cap:
                    try:
                        gives_check = board.gives_check(m)
                    except Exception:
                        gives_check = False
                    if not gives_check:
                        s -= 120
                if early and not is_cap and not board.is_castling(m):
                    if not self._is_start_square(piece.piece_type, piece.color, m.from_square):
                        to_center = chess.square_file(m.to_square) in (3, 4) and chess.square_rank(m.to_square) in (2, 3, 4, 5)
                        if not to_center:
                            s -= 70
                if piece.piece_type == chess.PAWN and early and not is_cap:
                    from_file = chess.square_file(m.from_square)
                    from_rank = chess.square_rank(m.from_square)
                    to_rank = chess.square_rank(m.to_square)
                    # Bishop kick patterns (a6 vs Bb5, h6 vs Bg5, g6 vs Bf5)
                    if piece.color == chess.BLACK:
                        if m.from_square == chess.H7 and m.to_square == chess.H6:
                            tgt = board.piece_at(chess.G5)
                            if tgt and tgt.color != piece.color and tgt.piece_type == chess.BISHOP:
                                s += 130
                        if m.from_square == chess.A7 and m.to_square == chess.A6:
                            tgt = board.piece_at(chess.B5)
                            if tgt and tgt.color != piece.color and tgt.piece_type == chess.BISHOP:
                                s += 120
                        if m.from_square == chess.G7 and m.to_square == chess.G6:
                            tgt = board.piece_at(chess.F5)
                            if tgt and tgt.color != piece.color and tgt.piece_type == chess.BISHOP:
                                s += 90
                    else:
                        if m.from_square == chess.H2 and m.to_square == chess.H3:
                            tgt = board.piece_at(chess.G4)
                            if tgt and tgt.color != piece.color and tgt.piece_type == chess.BISHOP:
                                s += 130
                        if m.from_square == chess.A2 and m.to_square == chess.A3:
                            tgt = board.piece_at(chess.B4)
                            if tgt and tgt.color != piece.color and tgt.piece_type == chess.BISHOP:
                                s += 120
                        if m.from_square == chess.G2 and m.to_square == chess.G3:
                            tgt = board.piece_at(chess.F4)
                            if tgt and tgt.color != piece.color and tgt.piece_type == chess.BISHOP:
                                s += 90
                    # Discourage early f-pawn push and also random wing pawn thrusts like a/b/g/h
                    if from_file == 5:
                        if piece.color == chess.WHITE and from_rank == 1 and to_rank == 2:
                            s -= 140
                        if piece.color == chess.BLACK and from_rank == 6 and to_rank == 5:
                            s -= 140
                    if from_file in (0, 1, 6, 7) and ((piece.color == chess.WHITE and from_rank == 1 and to_rank == 2) or (piece.color == chess.BLACK and from_rank == 6 and to_rank == 5)):
                        s -= 60
                    # Discourage early c-pawn push to c4/c5 if we already advanced the e-pawn (prevents e5+c5 blunder-y structures)
                    if from_file == 2:
                        e_pawn_sq = chess.E2 if piece.color == chess.WHITE else chess.E7
                        e_advanced = board.piece_at(e_pawn_sq) is None
                        if e_advanced and ((piece.color == chess.WHITE and from_rank == 1 and to_rank == 3) or (piece.color == chess.BLACK and from_rank == 6 and to_rank == 4)):
                            s -= 80
                    if chess.square_file(m.to_square) in (3, 4):
                        s += 50
            return s

        moves = list(board.legal_moves)
        moves.sort(key=score_move, reverse=True)
        return moves

    def _evaluate(self, board: chess.Board) -> float:
        # Terminal
        if board.is_checkmate():
            # If it's our turn and we're checkmated, that's bad for us
            return -100000
        if board.is_stalemate() or board.is_insufficient_material() or board.can_claim_draw():
            return 0

        # Base material (white minus black)
        material = 0
        piece_map = board.piece_map()
        for sq, pc in piece_map.items():
            val = self.piece_values[pc.piece_type]
            material += val if pc.color == chess.WHITE else -val

        # Doubled pawns penalty
        dp_pen = self._doubled_pawns_penalty(board)

        # Mobility (white - black) with small weight
        mob_w, mob_b = self._mobility(board)
        mobility_term = (mob_w - mob_b) * 1.0

        # Centralization: reward pieces in the center (white - black)
        center = {chess.C3, chess.D3, chess.E3, chess.F3, chess.C4, chess.D4, chess.E4, chess.F4,
                  chess.C5, chess.D5, chess.E5, chess.F5, chess.C6, chess.D6, chess.E6, chess.F6}
        center_score = 0
        for sq, pc in piece_map.items():
            if sq in center:
                w = 10 if pc.piece_type in (chess.KNIGHT, chess.BISHOP) else 5
                center_score += w if pc.color == chess.WHITE else -w

        # Rooks on open files
        rook_file_bonus = 0
        for sq, pc in piece_map.items():
            if pc.piece_type == chess.ROOK:
                file_idx = chess.square_file(sq)
                if self._is_open_file(board, file_idx):
                    rook_file_bonus += 15 if pc.color == chess.WHITE else -15

        # King safety: prefer castled in middlegame (queens/rooks present)
        safety = 0
        heavy_pieces = sum(1 for p in piece_map.values() if p.piece_type in (chess.QUEEN, chess.ROOK))
        if heavy_pieces >= 3:
            wk_sq = board.king(chess.WHITE)
            bk_sq = board.king(chess.BLACK)
            safety += self._king_safety_bonus(wk_sq, chess.WHITE)
            safety -= self._king_safety_bonus(bk_sq, chess.BLACK)
            # Penalize wandering kings early if not castled squares
            if self._is_early_game(board):
                if wk_sq not in (chess.E1, chess.G1, chess.C1):
                    safety -= 40
                if bk_sq not in (chess.E8, chess.G8, chess.C8):
                    safety += 40

        # Early queen raid penalty: queen deep in opponent camp in the opening
        queen_raid_pen = 0
        if self._is_early_game(board):
            q_w = board.pieces(chess.QUEEN, chess.WHITE)
            q_b = board.pieces(chess.QUEEN, chess.BLACK)
            if q_w:
                qsq = next(iter(q_w))
                # White queen on rank 7/8 is often risky early
                if chess.square_rank(qsq) >= 6:
                    queen_raid_pen -= 30
            if q_b:
                qsq = next(iter(q_b))
                # Black queen on rank 1/2 is often risky early
                if chess.square_rank(qsq) <= 1:
                    queen_raid_pen += 30

        # Piece-square tendencies (small)
        pst = self._pst_score(board)

        # Hanging/loose pieces penalty
        hanging_pen = self._hanging_pieces_penalty(board)

        # Aggregate white-centric score then convert to side-to-move via negamax
        white_score = material - dp_pen + mobility_term + center_score + rook_file_bonus + safety + queen_raid_pen + pst - hanging_pen
        return white_score if board.turn == chess.WHITE else -white_score

    def _opening_book_move(self, board: chess.Board) -> Optional[chess.Move]:
        # Only use book for the first few plies and only from starting positions
        if board.move_stack is None:
            return None
        if board.fullmove_number > 10:
            return None
        # Build UCI history from the start position
        hist = tuple(m.uci() for m in board.move_stack)
        # Try exact key; also try from a truncated start if someone inserted off-book early
        for klen in range(len(hist), -1, -1):
            key = hist[:klen]
            if key in self.opening_book:
                candidates = self.opening_book[key]
                # Filter to legal moves only
                legals = {m.uci(): m for m in board.legal_moves}
                legal_ucis = [u for u in candidates if u in legals]
                if legal_ucis:
                    # Choose the first candidate to be stable; could randomize if desired
                    return legals[legal_ucis[0]]
        return None

    def _is_start_square(self, piece_type: chess.PieceType, color: chess.Color, sq: int) -> bool:
        file_idx = chess.square_file(sq)
        rank_idx = chess.square_rank(sq)
        if piece_type == chess.KING:
            return (file_idx, rank_idx) == ((4, 0) if color == chess.WHITE else (4, 7))
        if piece_type == chess.QUEEN:
            return (file_idx, rank_idx) == ((3, 0) if color == chess.WHITE else (3, 7))
        if piece_type == chess.ROOK:
            return (file_idx, rank_idx) in ({(0, 0), (7, 0)} if color == chess.WHITE else {(0, 7), (7, 7)})
        if piece_type == chess.BISHOP:
            return (file_idx, rank_idx) in ({(2, 0), (5, 0)} if color == chess.WHITE else {(2, 7), (5, 7)})
        if piece_type == chess.KNIGHT:
            return (file_idx, rank_idx) in ({(1, 0), (6, 0)} if color == chess.WHITE else {(1, 7), (6, 7)})
        if piece_type == chess.PAWN:
            return rank_idx == (1 if color == chess.WHITE else 6)
        return False

    def _pst_score(self, board: chess.Board) -> int:
        score = 0
        for sq, pc in board.piece_map().items():
            file_idx = chess.square_file(sq)
            rank_idx = chess.square_rank(sq)
            sign = 1 if pc.color == chess.WHITE else -1
            if pc.piece_type == chess.KNIGHT:
                # Knights: center good, rim bad
                if file_idx in (0, 7):
                    score -= 20 * sign
                elif file_idx in (1, 6):
                    score -= 10 * sign
                if rank_idx in (0, 7):
                    score -= 10 * sign
                if (file_idx, rank_idx) in {(2, 2), (3, 2), (4, 2), (5, 2), (2, 3), (3, 3), (4, 3), (5, 3)}:
                    score += 15 * sign
            elif pc.piece_type == chess.BISHOP:
                # Bishops: prefer long diagonals and central ranks
                if rank_idx in (2, 3, 4, 5):
                    score += 5 * sign
            elif pc.piece_type == chess.PAWN:
                # Central pawns advanced are nice
                if file_idx in (3, 4):
                    score += rank_idx * 1 * sign if pc.color == chess.WHITE else (7 - rank_idx) * 1 * sign
        return score

    def _is_early_game(self, board: chess.Board) -> bool:
        # Quick heuristic for opening/middlegame
        heavy_pieces = sum(1 for p in board.piece_map().values() if p.piece_type in (chess.QUEEN, chess.ROOK))
        return heavy_pieces >= 3 and board.fullmove_number < 15

    def _most_minors_undeveloped(self, board: chess.Board, color: chess.Color) -> bool:
        # True if 3 or 4 minors still on back rank starting squares
        if color == chess.WHITE:
            starts = [chess.B1, chess.G1, chess.C1, chess.F1]
        else:
            starts = [chess.B8, chess.G8, chess.C8, chess.F8]
        cnt = 0
        for sq in starts:
            pc = board.piece_at(sq)
            if pc and pc.color == color and pc.piece_type in (chess.KNIGHT, chess.BISHOP):
                cnt += 1
        return cnt >= 3

    def _mobility(self, board: chess.Board) -> Tuple[int, int]:
        # Count legal moves for both sides using copies
        w_board = board if board.turn == chess.WHITE else board.copy(stack=False)
        if w_board.turn != chess.WHITE:
            w_board.turn = chess.WHITE
        b_board = board if board.turn == chess.BLACK else board.copy(stack=False)
        if b_board.turn != chess.BLACK:
            b_board.turn = chess.BLACK
        return sum(1 for _ in w_board.legal_moves), sum(1 for _ in b_board.legal_moves)

    def _is_open_file(self, board: chess.Board, file_idx: int) -> bool:
        # True if no pawns on this file (either color)
        for rank in range(8):
            sq = chess.square(file_idx, rank)
            pc = board.piece_at(sq)
            if pc and pc.piece_type == chess.PAWN:
                return False
        return True

    def _doubled_pawns_penalty(self, board: chess.Board) -> int:
        # Penalty in centipawns for doubled pawns (per extra pawn on a file)
        penalty = 0
        for color in (chess.WHITE, chess.BLACK):
            for file_idx in range(8):
                cnt = 0
                for rank in range(8):
                    sq = chess.square(file_idx, rank)
                    pc = board.piece_at(sq)
                    if pc and pc.piece_type == chess.PAWN and pc.color == color:
                        cnt += 1
                if cnt > 1:
                    penalty += (cnt - 1) * 12 * (1 if color == chess.WHITE else -1)
        return penalty

    def _king_safety_bonus(self, king_sq: int, color: chess.Color) -> int:
        # Bonus for castled-like positions in middlegame; penalty for center-exposed kings
        if king_sq is None:
            return 0
        file_idx = chess.square_file(king_sq)
        rank_idx = chess.square_rank(king_sq)
        if color == chess.WHITE:
            if (file_idx, rank_idx) in {(6, 0), (2, 0)}:
                return 20
            if (file_idx, rank_idx) in {(4, 0), (3, 0)}:
                return -10
        else:
            if (file_idx, rank_idx) in {(6, 7), (2, 7)}:
                return 20
            if (file_idx, rank_idx) in {(4, 7), (3, 7)}:
                return -10
        return 0

    # --- Tactical helpers ---
    def _see_value(self, board: chess.Board, move: chess.Move) -> int:
        """Static Exchange Evaluation for a move in centipawns.

        Positive is good for the side to move. Uses python-chess SEE when available.
        """
        if hasattr(board, "see"):
            return int(board.see(move))
        # Fallback MVV/LVA approximation
        victim = board.piece_at(move.to_square)
        attacker = board.piece_at(move.from_square)
        if not attacker:
            return 0
        gain = 0
        if victim:
            gain += self.piece_values.get(victim.piece_type, 0)
        gain -= self.piece_values.get(attacker.piece_type, 0)
        return gain

    def _hanging_pieces_penalty(self, board: chess.Board) -> int:
        """Penalty for pieces that can be captured for non-negative SEE by the opponent."""
        pen_white = 0
        pen_black = 0
        # Evaluate from a neutral board state without mutating turn logic
        for sq, pc in board.piece_map().items():
            if pc.piece_type == chess.KING:
                continue
            opp = not pc.color
            # If opponent has a legal capture on this square with SEE >= 0, penalize
            attackers = board.attackers(opp, sq)
            if not attackers:
                continue
            bad = False
            for a in attackers:
                m = chess.Move(a, sq)
                if m in board.legal_moves:
                    try:
                        see_gain = self._see_value(board, m)
                    except Exception:
                        see_gain = self.piece_values.get(pc.piece_type, 0) - 1
                    if see_gain >= 0:
                        bad = True
                        break
            if bad:
                val = int(self.piece_values.get(pc.piece_type, 0) * 0.33)
                if pc.color == chess.WHITE:
                    pen_white += val
                else:
                    pen_black += val
        # Convert to white-centric score
        return pen_white - pen_black

    # --- Risk/Pattern helpers ---
    def _is_bishop_sac_on_f2f7(self, board: chess.Board, move: chess.Move) -> bool:
        pc = board.piece_at(move.from_square)
        if not pc or pc.piece_type != chess.BISHOP:
            return False
        # Only consider captures of the f-pawn on its home square
        target = chess.F2 if pc.color == chess.BLACK else chess.F7
        if move.to_square != target:
            return False
        if not board.is_capture(move):
            return False
        victim = board.piece_at(move.to_square)
        if not victim or victim.piece_type != chess.PAWN:
            return False
        # Typically it's tempting because it's check; if not a check, still likely bad
        try:
            is_check = board.gives_check(move)
        except Exception:
            is_check = False
        return True

    def _risk_score(self, board: chess.Board, move: chess.Move) -> int:
        """Lower is safer. Positive values indicate tactical/material risk for the mover."""
        risk = 0
        # Negative SEE means we may be losing material on this move
        try:
            see = int(self._see_value(board, move))
        except Exception:
            see = 0
        if see < 0:
            risk += -see
        # Extra risk for early bishop sac on f2/f7
        if self._is_early_game(board) and self._is_bishop_sac_on_f2f7(board, move):
            risk += 600
        # Queen trap risk (e.g., greedy corner rook grabs like Qxh8?)
        try:
            risk += self._queen_trap_risk(board, move)
        except Exception:
            pass
        return risk

    def _queen_trap_risk(self, board: chess.Board, move: chess.Move) -> int:
        """Estimate risk of the mover's queen becoming trapped or heavily attacked after this move.

        Adds a notable penalty for queen captures on corner rooks when defenders outweigh attackers
        or when the queen has very limited safe mobility from the destination square.
        """
        pc = board.piece_at(move.from_square)
        if not pc or pc.piece_type != chess.QUEEN:
            return 0

        # Pre-move info about target square
        victim_pre = board.piece_at(move.to_square)
        is_corner = move.to_square in {chess.A8, chess.H8, chess.A1, chess.H1}
        is_corner_rook_capture = bool(victim_pre and victim_pre.piece_type == chess.ROOK and is_corner)

        # Simulate the move
        board.push(move)
        try:
            my_color = not board.turn  # after push, side to move flipped; queen belongs to the previous mover
            qsq = move.to_square
            risk = 0

            # If queen moved to a corner, that's typically risky (limited squares)
            if qsq in {chess.A8, chess.H8, chess.A1, chess.H1}:
                risk += 120

            # Count attackers/defenders on the queen's square
            attackers = len(board.attackers(not my_color, qsq))
            defenders = len(board.attackers(my_color, qsq))
            if attackers >= max(1, defenders):
                # Heavily attacked or under-defended queen on destination
                risk += 350

            # Estimate queen mobility: how many immediate moves are not landing on attacked squares
            safe_exits = 0
            for m in board.legal_moves:
                if m.from_square == qsq:
                    # Quick static safety: avoid landing on currently attacked squares
                    if not board.is_attacked_by(not my_color, m.to_square):
                        safe_exits += 1
                        if safe_exits >= 4:
                            break
            if safe_exits <= 1:
                risk += 450
            elif safe_exits <= 3:
                risk += 200
            # Extra penalty if this was a corner rook capture and exits are limited or square is contested
            if is_corner_rook_capture:
                base = 300
                # If heavily attacked or exits are poor, escalate
                if attackers >= max(1, defenders) or safe_exits <= 2:
                    base += 600
                # Taking with check is often tempting; still risky. Keep the penalty significant.
                risk += base
        finally:
            board.pop()
        return risk
