#!/usr/bin/env python3
"""Generate pytest cases from one or more lichess analysis logs.

Input: log files that contain a "Columns:" section and a "PGN:" section.
We'll extract each row where class==Blunder, reconstruct the FEN of the
position before the blunder, and the blunder move in UCI. Then we'll write
parametrized pytest files that assert the engine does not pick that same
blunder move from those positions.

Where logs are loaded from:
    - By default (no arguments), all logs in the "past_games" folder located
        next to this script will be processed (files matching lichess_bot_game_*.log).
    - If a single argument is provided and it's a file path, that file is used.
    - If a single argument looks like a game id (e.g. OVmR29MI), the script will
        look for past_games/lichess_bot_game_<gameid>.log next to this script.

Usage examples:
    # Process all logs in tools/past_games
    python PYTHON/lichess_bot/tools/generate_blunder_tests.py

    # Process a specific game by id from tools/past_games
    python PYTHON/lichess_bot/tools/generate_blunder_tests.py OVmR29MI

    # Process an explicit file path
    python PYTHON/lichess_bot/tools/generate_blunder_tests.py \
        /path/to/lichess_bot_game_xxxxx.log

It will create files like:
    PYTHON/lichess_bot/tests/test_blunders_<gameid>.py

Dependencies: python-chess, pytest (already in requirements.txt)
"""

from __future__ import annotations

from dataclasses import dataclass
import io
import logging
import os
import re
import sys

import chess
import chess.pgn

logging.basicConfig(level=logging.INFO)

# Expected columns in the log file:
# ply, side, move, played_eval, best_eval, loss, class, best_suggestion
EXPECTED_COLUMNS = 8


@dataclass
class Blunder:
    """Data class representing a blunder move from analysis."""

    ply: int
    side: str  # 'W' or 'B'
    san: str  # SAN of the played blunder
    best_suggestion_san: str  # SAN of the best suggestion from log (mandatory)


def parse_columns_for_blunders(text: str) -> list[Blunder]:
    """Parse the Columns section of a log file to extract blunders."""
    lines = text.splitlines()
    # Find start of "Columns:" block
    try:
        idx = next(i for i, ln in enumerate(lines) if ln.strip().startswith("Columns:"))
    except StopIteration:
        return []

    blunders: list[Blunder] = []
    # Lines after header until a blank line or "PGN:" marker
    for ln in lines[idx + 1 :]:
        if not ln.strip():
            break
        if ln.strip().startswith("PGN:"):
            break
        # Expect lines starting with a move number
        if not re.match(r"^\s*\d+\s+", ln):
            continue
        # Split by 2+ spaces to get columns
        parts = re.split(r"\s{2,}", ln.strip())
        # Expected columns:
        # ply, side, move, played_eval, best_eval, loss, class, best_suggestion
        if len(parts) < EXPECTED_COLUMNS:
            continue
        try:
            ply = int(parts[0])
        except ValueError:
            continue
        side = parts[1]
        move_san = parts[2]
        clazz = parts[6]
        best_suggestion_san = parts[7].strip() if parts[7] else ""
        if clazz == "Blunder":
            # Require best suggestion to be provided; if it's missing, raise
            if not best_suggestion_san:
                msg = (
                    f"Missing best_suggestion in Columns "
                    f"for blunder row: ply={ply} side={side} "
                    f"move={move_san}.\nRaw line: '{ln.strip()}'"
                )
                raise ValueError(msg)
            blunders.append(
                Blunder(
                    ply=ply,
                    side=side,
                    san=move_san,
                    best_suggestion_san=best_suggestion_san,
                )
            )
    return blunders


def extract_pgn(text: str) -> str | None:
    """Extract the PGN block from a log file."""
    # Extract the PGN block after a line that is exactly 'PGN:' or starts with it
    m = re.search(r"^PGN:\s*$", text, flags=re.MULTILINE)
    if not m:
        return None
    start = m.end()
    pgn = text[start:].strip()
    return pgn if pgn else None


def san_list_from_game(game: chess.pgn.Game) -> list[str]:
    """Extract the list of SAN moves from a PGN game."""
    san_moves: list[str] = []
    node = game
    while node.variations:
        node = node.variation(0)
        san_moves.append(node.san())
    return san_moves


def fen_and_uci_for_blunders(
    pgn_text: str, blunders: list[Blunder]
) -> list[tuple[str, str, str, Blunder]]:
    """Convert blunders to (FEN, UCI, best_UCI, Blunder) tuples."""
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if game is None:
        msg = "Failed to parse PGN from log"
        raise RuntimeError(msg)

    main_sans = san_list_from_game(game)
    results: list[tuple[str, str, str, Blunder]] = []
    for bl in blunders:
        # Reconstruct the board before this ply
        board = game.board()
        # plies are 1-based; apply moves up to ply-1
        upto = max(0, bl.ply - 1)
        for i in range(min(upto, len(main_sans))):
            board.push_san(main_sans[i])
        fen_before = board.fen()
        # Parse the SAN blunder at this position to get UCI. If parse fails, skip.
        try:
            move = board.parse_san(bl.san)
        except ValueError:
            # Try to fall back to using the game's move at that ply if available
            if bl.ply - 1 < len(main_sans):
                try:
                    move = board.parse_san(main_sans[bl.ply - 1])
                except Exception:
                    continue
            else:
                continue
        # Parse best suggestion SAN to UCI in the same position;
        # if it fails, skip this blunder
        try:
            best_move = board.parse_san(bl.best_suggestion_san)
            best_uci = best_move.uci()
        except Exception as e:
            msg = (
                f"Failed to parse best_suggestion SAN "
                f"'{bl.best_suggestion_san}' at ply {bl.ply} "
                f"side {bl.side} in position FEN: {fen_before}. "
                f"Error: {e}"
            )
            raise ValueError(msg)
        results.append((fen_before, move.uci(), best_uci, bl))
    return results


def ensure_unified_test_file(target_path: str) -> None:
    """Create the unified test file skeleton if it doesn't exist."""
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    if os.path.exists(target_path):
        return
    # Create skeleton unified test file
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(
            """import os
import sys
import chess
import pytest

# Ensure repo root is importable when running pytest directly
REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from PYTHON.lichess_bot.engine import RandomEngine  # noqa: E402

BLUNDER_CASES = [
]


@pytest.mark.parametrize(
    'fen,blunder_uci,label',
    BLUNDER_CASES,
    ids=[c[2] for c in BLUNDER_CASES],
)
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
    assert move.uci() != blunder_uci, (
        f'Engine repeated blunder {blunder_uci} at {label}. '
        f'Explanation: {explanation}'
    )
"""
        )


def append_cases_to_unified_test(
    unified_path: str, cases: list[tuple[str, str, str, Blunder]]
) -> int:
    """Append new cases to BLUNDER_CASES in the unified test file, skipping duplicates.

    Returns the number of cases actually appended.
    """
    ensure_unified_test_file(unified_path)
    with open(unified_path, encoding="utf-8") as f:
        content = f.read()

    # Extract current cases as a set of (fen, uci) to de-duplicate
    existing = set(
        re.findall(
            r"\(\"(.*?)\",\s*\"(.*?)\",\s*\"ply\d+_[WB]_[^\"]+\"\)\,?",
            content,
            flags=re.DOTALL,
        )
    )

    lines = []
    updated_existing = 0
    for fen, uci, best_uci, bl in cases:
        key = (fen, uci)
        if key in existing:
            # If a best move UCI is available, try to backfill
            # or update it into the label
            if best_uci:
                side = "W" if bl.side == "W" else "B"
                fen_re = re.escape(fen)
                uci_re = re.escape(uci)
                base_label = f"ply{bl.ply}_{side}_{uci}"
                # Pattern A: no best suffix yet
                pattern_no_best = (
                    rf"\(\"{fen_re}\",\s*\"{uci_re}\","
                    rf"\s*\"({re.escape(base_label)})\"\)"
                )
                # Pattern B: existing best suffix (whatever it is)
                # replace it with the new best_uci
                pattern_with_best = (
                    rf"\(\"{fen_re}\",\s*\"{uci_re}\","
                    rf"\s*\"({re.escape(base_label)}_best_[^\"]+)\"\)"
                )
                if re.search(pattern_no_best, content):
                    content = re.sub(
                        pattern_no_best,
                        lambda m: m.group(0).replace(
                            m.group(1), f"{base_label}_best_{best_uci}"
                        ),
                        content,
                        count=1,
                    )
                    updated_existing += 1
                elif re.search(pattern_with_best, content):
                    content = re.sub(
                        pattern_with_best,
                        lambda m: m.group(0).replace(
                            m.group(1), f"{base_label}_best_{best_uci}"
                        ),
                        content,
                        count=1,
                    )
                    updated_existing += 1
            continue
        label = f"ply{bl.ply}_{'W' if bl.side == 'W' else 'B'}_{uci}"
        # Encode the best move UCI in the label so tests can
        # extract it without changing tuple shape
        label += f"_best_{best_uci}"
        lines.append(f'    ("{fen}", "{uci}", "{label}"),\n')

    if not lines:
        return 0

    # Insert before closing bracket of BLUNDER_CASES into the possibly updated 'content'
    new_content = re.sub(
        r"BLUNDER_CASES\s*=\s*\[\n",
        lambda m: m.group(0) + "".join(lines),
        content,
        count=1,
    )

    # Apply the changes (either updates to existing labels and/or appended lines)
    with open(unified_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    return len(lines) + updated_existing


def _process_single_log(log_path: str) -> int:
    """Process a single log file. Returns 0 on success, non-zero otherwise."""
    try:
        with open(log_path, encoding="utf-8") as fh:
            text = fh.read()
    except FileNotFoundError:
        logging.exception(f"Log file not found: {log_path}")
        return 2

    try:
        blunders = parse_columns_for_blunders(text)
    except Exception as e:
        logging.exception(f"Error parsing Columns in {os.path.basename(log_path)}: {e}")
        return 2
    if not blunders:
        logging.warning(
            f"No blunders found in Columns section: {os.path.basename(log_path)}"
        )
        return 1

    pgn_text = extract_pgn(text)
    if not pgn_text:
        logging.warning(f"No PGN section found: {os.path.basename(log_path)}")
        return 1

    try:
        cases = fen_and_uci_for_blunders(pgn_text, blunders)
    except Exception as e:
        logging.exception(
            f"Error converting SAN to UCI in {os.path.basename(log_path)}: {e}"
        )
        return 2
    if not cases:
        logging.warning(
            f"Failed to reconstruct any blunder positions "
            f"from PGN: {os.path.basename(log_path)}"
        )
        return 1

    base = os.path.basename(log_path)
    m = re.search(r"game_([A-Za-z0-9]+)\.log$", base)
    game_id = m.group(1) if m else os.path.splitext(base)[0]

    # Always append to the unified test file
    unified = os.path.join(
        os.path.dirname(__file__), "..", "tests", "test_blunders_all.py"
    )
    unified = os.path.abspath(unified)
    added = append_cases_to_unified_test(unified, cases)
    logging.info(
        f"Appended {added} new blunder checks to "
        f"{os.path.relpath(unified)} (game {game_id})."
    )
    return 0


def main(argv: list[str]) -> int:
    """Process log files and generate blunder test cases."""
    script_dir = os.path.dirname(__file__)
    past_dir = os.path.abspath(os.path.join(script_dir, "past_games"))

    # No argument: process all logs in past_games
    if len(argv) == 1:
        if not os.path.isdir(past_dir):
            logging.error(f"No past_games directory found at {past_dir}")
            return 2
        logs = [
            os.path.join(past_dir, name)
            for name in os.listdir(past_dir)
            if re.match(r"lichess_bot_game_[A-Za-z0-9]+\.log$", name)
        ]
        if not logs:
            logging.warning(f"No logs found in {past_dir}")
            return 1
        # Sort by mtime ascending for determinism
        logs.sort(key=lambda p: os.path.getmtime(p))
        ok = 0
        for lp in logs:
            rc = _process_single_log(lp)
            if rc == 0:
                ok += 1
        logging.info(
            f"Processed {len(logs)} logs from {past_dir}, "
            f"succeeded: {ok}, failed: {len(logs) - ok}"
        )
        return 0 if ok > 0 else 1

    # One argument: game id or file path
    arg = argv[1]
    candidate_path = None
    if os.path.isfile(arg):
        candidate_path = arg
    # Treat as game id, resolve within past_games
    elif re.fullmatch(r"[A-Za-z0-9]+", arg):
        candidate_path = os.path.join(past_dir, f"lichess_bot_game_{arg}.log")
    else:
        # Fallback: if it's a bare filename, try inside past_games
        maybe = os.path.join(past_dir, arg)
        if os.path.isfile(maybe):
            candidate_path = maybe

    if not candidate_path:
        logging.info("Usage: generate_blunder_tests.py [<game_id>|</path/to/log>]")
        return 2

    return _process_single_log(candidate_path)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
