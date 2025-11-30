#!/usr/bin/env bash
set -euo pipefail

# Resolve script directory and repo root
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"

# Load a local .env if present
if [[ -f "$SCRIPT_DIR/.env" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$SCRIPT_DIR/.env"
  set +a
fi

# Helper to persist the token to .env
save_token() {
  local env_file="$SCRIPT_DIR/.env"
  # Keep other lines, remove existing LICHESS_TOKEN, then append new one
  if [[ -f "$env_file" ]]; then
    grep -v '^LICHESS_TOKEN=' "$env_file" > "$env_file.tmp" || true
    printf 'LICHESS_TOKEN=%s\n' "$LICHESS_TOKEN" >> "$env_file.tmp"
    mv "$env_file.tmp" "$env_file"
  else
    printf 'LICHESS_TOKEN=%s\n' "$LICHESS_TOKEN" > "$env_file"
  fi
  chmod 600 "$env_file" 2>/dev/null || true
  echo "Saved token to $env_file"
}

# Optional: --token <TOKEN> to set for this run
if [[ "${1:-}" == "--token" || "${1:-}" == "-t" ]]; then
  if [[ "${2:-}" == "" ]]; then
    echo "--token requires a value"
    exit 2
  fi
  export LICHESS_TOKEN="$2"
  shift 2
fi

# Ask for token if not set and export it for this run
if [[ -z "${LICHESS_TOKEN:-}" ]]; then
  printf "Paste your Lichess API token and press Enter: "
  read -r token
  export LICHESS_TOKEN="$token"
  if [[ -z "$LICHESS_TOKEN" ]]; then
    echo "No token provided. Aborting."
    exit 1
  fi
  echo "Token received."
  save_token
else
  # If token came from CLI or env, still persist so next run won't prompt
  save_token
fi

# Choose python: prefer local venv
PY="$SCRIPT_DIR/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  PY="python"
fi

cd "$REPO_ROOT"
echo "Using Python: $PY"
echo "Repository root: $REPO_ROOT"
echo "Starting Lichess bot..."
echo "Tip: Open another terminal to watch logs; press Ctrl+C here to stop."

trap 'echo; echo "Stopping bot (Ctrl+C)."' INT
"$PY" -m PYTHON.lichess_bot.main "$@"
