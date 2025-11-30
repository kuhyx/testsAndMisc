#!/usr/bin/env bash
set -euo pipefail

# Resolve paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
VENV_DIR="$REPO_ROOT/.venv"

# Find analyzer script (prefer local copy in this folder, fallback to PYTHON/analyze_chess_game.py)
ANALYZER="$SCRIPT_DIR/analyze_chess_game.py"
if [[ ! -f "$ANALYZER" ]]; then
  if [[ -f "$REPO_ROOT/PYTHON/analyze_chess_game.py" ]]; then
    ANALYZER="$REPO_ROOT/PYTHON/analyze_chess_game.py"
  else
    echo "Could not find analyze_chess_game.py" >&2
    exit 1
  fi
fi

# Ensure virtual environment exists and is active
if [[ ! -d "$VENV_DIR" ]]; then
  python3 -m venv "$VENV_DIR"
fi
# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"

# Install dependencies quietly
pip install -r "$SCRIPT_DIR/requirements.txt" >/dev/null

# Default engine (can override with STOCKFISH env var)
ENGINE_BIN="${STOCKFISH:-stockfish}"

# Require input file or auto-pick a lichess log if not provided
if [[ $# -eq 0 ]]; then
  GAME_FILE="$(ls -1 "$REPO_ROOT"/lichess_bot_game_*.log 2>/dev/null | head -n1 || true)"
  if [[ -z "${GAME_FILE:-}" ]]; then
    echo "Usage: $0 <pgn-or-log-file> [--time sec | --depth N] [--engine path] [extra args]" >&2
    exit 2
  fi
  set -- "$GAME_FILE"
fi

# Pass through args, but add --engine if user didn't include one
if printf '%s\n' "$@" | grep -q -- "--engine"; then
  ENGINE_ARGS=()
else
  ENGINE_ARGS=(--engine "$ENGINE_BIN")
fi

python "$ANALYZER" "$@" "${ENGINE_ARGS[@]}"
