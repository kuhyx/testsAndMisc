#!/usr/bin/env bash
set -euo pipefail

# Run Mini Articles (backend + frontend)
# Options (env): HOST (default 127.0.0.1), PORT (default 8000), ARTICLES_DATA_DIR

DIR=$(cd -- "$(dirname -- "$0")" && pwd)
SITE_DIR="$DIR"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
PYTHON_BIN="${PYTHON:-}"

if [[ -z "${PYTHON_BIN}" ]]; then
  if command -v python >/dev/null 2>&1; then PYTHON_BIN=python
  elif command -v python3 >/dev/null 2>&1; then PYTHON_BIN=python3
  else
    echo "Python is required but not found in PATH." >&2
    exit 1
  fi
fi

if [[ ! -f "$SITE_DIR/server.py" ]]; then
  echo "server.py not found in $SITE_DIR" >&2
  exit 1
fi

# Start server in background
export HOST PORT ARTICLES_DATA_DIR
"$PYTHON_BIN" "$SITE_DIR/server.py" &
SRV_PID=$!
trap 'kill $SRV_PID 2>/dev/null || true' EXIT INT TERM

# Give it a moment to start
sleep 0.5
URL="http://$HOST:$PORT/"

# Try to open browser on Linux
if command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$URL" >/dev/null 2>&1 || true
fi

echo "Mini Articles running at $URL"

echo "Press Ctrl+C to stop."
# Wait on server
wait "$SRV_PID"
