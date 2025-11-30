"""Chess engine wrapper for the C-based random/scoring engine."""

import json
import os
import subprocess

import chess


class RandomEngine:
    """Thin wrapper around the C engine in C/lichess_random_engine/random_engine.

    Contract:
    - Given a chess.Board, call the C binary with all legal moves encoded as
      UCI (with optional annotations in the future). The binary prints the
      chosen move's UCI on stdout (or JSON when --explain, which we don't need).
    - We do not compute or rank anything in Python; we just pass through moves
      and play exactly what the engine returns.
    - If the binary is missing or returns an invalid/illegal move, raise.
    """

    def __init__(
        self,
        *,
        engine_path: str | None = None,
        max_time_sec: float = 2.0,
        depth: int | None = None,
    ):
        """Initialize the engine wrapper with path and time settings."""
        self.max_time_sec = max_time_sec
        # depth is accepted for compatibility with existing callers but is unused;
        # the C engine handles its own scoring/selection.
        self.depth = depth
        # Default relative path inside this repo
        default_path = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "..",
                "C",
                "lichess_random_engine",
                "random_engine",
            )
        )
        self.engine_path = engine_path or default_path
        if not os.path.isfile(self.engine_path) or not os.access(
            self.engine_path, os.X_OK
        ):
            msg = (
                f"C engine not found or not executable at '{self.engine_path}'. "
                "Build it first (make -C C/lichess_random_engine)."
            )
            raise FileNotFoundError(msg)

    def _call_engine(self, args: list[str], *, timeout: float) -> str:
        try:
            proc = subprocess.run(
                [self.engine_path, *args],
                capture_output=True,
                text=True,
                timeout=timeout,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            stderr = (e.stderr or "").strip()
            msg = f"C engine failed: {stderr or e}"
            raise RuntimeError(msg) from e
        except subprocess.TimeoutExpired as e:
            msg = "C engine timed out"
            raise TimeoutError(msg) from e
        return (proc.stdout or "").strip()

    def choose_move(self, board: chess.Board) -> chess.Move:
        """Choose a move for the given board position."""
        mv, _ = self.choose_move_with_explanation(
            board, time_budget_sec=self.max_time_sec
        )
        return mv

    def choose_move_with_explanation(
        self, board: chess.Board, *, time_budget_sec: float
    ) -> tuple[chess.Move | None, str]:
        """Choose a move and return explanation for the decision."""
        # Collect legal moves and send to engine as plain UCI tokens.
        legal = list(board.legal_moves)
        if not legal:
            return None, "no_legal_moves"

        args = ["--fen", board.fen()] + [m.uci() for m in legal]
        # Optionally pass a seed for reproducibility when desired;
        # keep default behavior otherwise.
        # We deliberately avoid adding annotations here per request.

        output = self._call_engine(args, timeout=max(0.1, time_budget_sec))

        # The engine, without --explain, should print the chosen UCI.
        chosen_uci = output.splitlines()[-1].strip() if output else ""
        try:
            move = chess.Move.from_uci(chosen_uci)
        except Exception:
            msg = f"Engine returned invalid move: '{chosen_uci}' (output: {output!r})"
            raise RuntimeError(msg)

        if move not in board.legal_moves:
            msg = f"Engine returned illegal move for position: {chosen_uci}"
            raise RuntimeError(msg)

        return move, "from_c_engine"

    def evaluate_proposed_move_with_suggestion(
        self,
        board: chess.Board,
        proposed_move_uci: str,
        *,
        time_budget_sec: float,
    ) -> tuple[float, str, chess.Move | None, str]:
        """Ask the C engine to explain and analyze a specific candidate.

        Returns (candidate_score, candidate_expl, best_move, best_expl)
        where explanations are concise JSON snippets from the engine. All logic is
        delegated to the C binary; no scoring is done in Python.
        """
        legal = list(board.legal_moves)
        if not legal:
            return 0.0, "no_legal_moves", None, "no_best_move"

        args = ["--fen", board.fen(), "--explain", "--analyze", proposed_move_uci] + [
            m.uci() for m in legal
        ]
        out = self._call_engine(args, timeout=max(0.1, time_budget_sec))

        # Try to parse the engine's JSON explanation
        cand_score = 0.0
        best_move: chess.Move | None = None
        cand_expl = out
        best_expl = out
        try:
            data = json.loads(out)
            # candidate score if provided
            analyze = data.get("analyze") or {}
            cs = analyze.get("candidate_score")
            if isinstance(cs, int | float):
                cand_score = float(cs)
            # best move
            chosen = data.get("chosen_move")
            if isinstance(chosen, str):
                try:
                    bm = chess.Move.from_uci(chosen)
                    if bm in board.legal_moves:
                        best_move = bm
                except Exception:
                    best_move = None
            # Store compact explanations for debugging
            cand_expl = json.dumps(analyze, ensure_ascii=False)
            best_expl = json.dumps(
                {
                    "chosen_index": data.get("chosen_index"),
                    "chosen_move": data.get("chosen_move"),
                },
                ensure_ascii=False,
            )
        except Exception:
            # Leave defaults with raw output text
            pass

        return cand_score, cand_expl, best_move, best_expl
