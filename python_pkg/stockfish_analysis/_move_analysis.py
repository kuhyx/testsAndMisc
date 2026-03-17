"""Move scoring, classification, and single-move analysis helpers."""

from __future__ import annotations

from dataclasses import dataclass

import chess
import chess.engine


def score_to_cp(
    score: chess.engine.PovScore, *, pov_white: bool
) -> tuple[int | None, int | None]:
    """Return tuple (cp, mate_in) from a PovScore for the given POV color.

    If it's a mate score, cp will be None and mate_in will be +/-N
    (positive means mate for POV side). If it's a cp score, mate_in will be None.
    """
    pov = chess.WHITE if pov_white else chess.BLACK
    s = score.pov(pov)
    if s.is_mate():
        mi = s.mate()
        return None, mi
    return s.score(mate_score=None), None


# Centipawn loss thresholds for move quality classification (Lichess-like bands)
CP_LOSS_BEST = 10
CP_LOSS_EXCELLENT = 20
CP_LOSS_GOOD = 50
CP_LOSS_INACCURACY = 99
CP_LOSS_MISTAKE = 299


# Centipawn loss thresholds for move classification
_CP_LOSS_BANDS = [
    (CP_LOSS_BEST, "Best"),
    (CP_LOSS_EXCELLENT, "Excellent"),
    (CP_LOSS_GOOD, "Good"),
    (CP_LOSS_INACCURACY, "Inaccuracy"),
    (CP_LOSS_MISTAKE, "Mistake"),
]


def classify_cp_loss(cp_loss: int | None) -> str:
    """Classify move quality using Lichess-like centipawn loss bands.

    Loss is best_eval(cp) - played_eval(cp), from the mover's POV (positive is worse).
    Bands (approx, widely cited):
      - Best:    0..10 cp
      - Excellent: 11..20 cp
      - Good:    21..50 cp
      - Inaccuracy: 51..99 cp
      - Mistake: 100..299 cp
      - Blunder: >=300 cp
    """
    if cp_loss is None:
        return "Unknown"
    for threshold, classification in _CP_LOSS_BANDS:
        if cp_loss <= threshold:
            return classification
    return "Blunder"


def fmt_eval(cp: int | None, mate_in: int | None) -> str:
    """Format evaluation score as human-readable string."""
    if mate_in is not None:
        sign = "+" if mate_in > 0 else ""
        return f"M{sign}{mate_in}"
    if cp is None:
        return "?"
    # Convert cp to pawns with sign and 2 decimals
    return f"{cp / 100.0:+.2f}"


@dataclass
class MoveAnalysis:
    """Container for single move analysis results."""

    san: str
    best_san: str
    played_cp: int | None
    played_mate: int | None
    best_cp: int | None
    best_mate: int | None
    cp_loss: int | None
    classification: str


@dataclass
class AnalysisContext:
    """Container for analysis parameters passed between functions."""

    engine: chess.engine.SimpleEngine
    limit: chess.engine.Limit
    multipv: int


def _get_best_move(
    engine: chess.engine.SimpleEngine,
    board: chess.Board,
    limit: chess.engine.Limit,
    multipv: int,
) -> chess.Move | None:
    """Get the engine's best move for a position."""
    info_raw = engine.analyse(board, limit=limit, multipv=multipv)
    info = info_raw[0] if isinstance(info_raw, list) else info_raw
    if info is not None and "pv" in info and info["pv"]:
        return info["pv"][0]
    res = engine.play(board, limit)
    return res.move


def _evaluate_position(
    engine: chess.engine.SimpleEngine,
    board: chess.Board,
    limit: chess.engine.Limit,
    multipv: int,
    *,
    pov_white: bool,
) -> tuple[int | None, int | None]:
    """Evaluate a position and return (cp, mate_in) from POV."""
    info_raw = engine.analyse(board, limit=limit, multipv=multipv)
    info = info_raw[0] if isinstance(info_raw, list) else info_raw
    if info is None or "score" not in info:
        return None, None
    return score_to_cp(info["score"], pov_white=pov_white)


def _classify_mate_move(best_mate: int | None, played_mate: int | None) -> str:
    """Classify a move when mate scores are involved."""
    if best_mate is None or played_mate is None:
        return "Blunder"
    if (best_mate > 0) and (played_mate > 0):
        if abs(played_mate) > abs(best_mate):
            return "Inaccuracy"
        return "Best"
    if (best_mate < 0) and (played_mate < 0):
        if abs(played_mate) < abs(best_mate):
            return "Blunder"
        return "Best" if abs(played_mate) == abs(best_mate) else "Good"
    return "Blunder"


def _analyze_single_move(
    ctx: AnalysisContext, board: chess.Board, move: chess.Move
) -> MoveAnalysis:
    """Analyze a single move and return analysis data."""
    mover_white = board.turn
    san = board.san(move)

    best_move = _get_best_move(ctx.engine, board, ctx.limit, ctx.multipv)
    best_san = board.san(best_move) if best_move is not None else "?"

    board_played = board.copy()
    board_played.push(move)
    played_cp, played_mate = _evaluate_position(
        ctx.engine, board_played, ctx.limit, ctx.multipv, pov_white=mover_white
    )

    if best_move is not None:
        board_best = board.copy()
        board_best.push(best_move)
        best_cp, best_mate = _evaluate_position(
            ctx.engine, board_best, ctx.limit, ctx.multipv, pov_white=mover_white
        )
    else:
        best_cp, best_mate = None, None

    cp_loss: int | None = None
    if best_mate is not None or played_mate is not None:
        classification = _classify_mate_move(best_mate, played_mate)
    elif best_cp is not None and played_cp is not None:
        cp_loss = max(0, best_cp - played_cp)
        classification = classify_cp_loss(cp_loss)
    else:
        classification = "Unknown"

    return MoveAnalysis(
        san=san,
        best_san=best_san,
        played_cp=played_cp,
        played_mate=played_mate,
        best_cp=best_cp,
        best_mate=best_mate,
        cp_loss=cp_loss,
        classification=classification,
    )
