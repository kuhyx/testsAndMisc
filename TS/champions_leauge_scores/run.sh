#!/usr/bin/env bash
set -Eeuo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

echo "[run] Working dir: $HERE"

if ! command -v node >/dev/null 2>&1; then
  echo "[run] Node.js is required. Please install Node.js >= 18." >&2
  exit 1
fi
if ! command -v npm >/dev/null 2>&1; then
  echo "[run] npm is required. Please install npm." >&2
  exit 1
fi

if [[ ! -f .env ]]; then
  if [[ -f .env.example ]]; then
    echo "[run] No .env found. Creating one from .env.example"
    cp -n .env.example .env || true
  else
    echo "[run] .env file missing and .env.example not found."
  fi
fi

free_port() {
  local port="$1"
  local attempts=0
  local pids=""
  if command -v lsof >/dev/null 2>&1; then
    pids=$(lsof -ti tcp:"$port" || true)
  fi
  if [[ -z "$pids" ]] && command -v fuser >/dev/null 2>&1; then
    # fuser prints PIDs and returns 0 if in use
    if fuser -n tcp "$port" >/dev/null 2>&1; then
      pids=$(fuser -n tcp "$port" 2>/dev/null | tr ' ' '\n' | tr -d '\n')
    fi
  fi
  if [[ -n "$pids" ]]; then
    echo "[run] Port $port in use by: $pids — terminating..."
    kill $pids || true
    # wait until freed (up to ~5s), escalate if needed
    while [[ $attempts -lt 25 ]]; do
      sleep 0.2
      if command -v lsof >/dev/null 2>&1; then
        lsof -ti tcp:"$port" >/dev/null || break
      else
        break
      fi
      attempts=$((attempts+1))
    done
    if command -v lsof >/dev/null 2>&1 && lsof -ti tcp:"$port" >/dev/null; then
      echo "[run] Port $port still busy — forcing kill..."
      kill -9 $pids || true
      sleep 0.2
    fi
  fi
}

echo "[run] Ensuring ports 5173 and 8787 are free..."
free_port 5173 || true
free_port 8787 || true

echo "[run] Installing dependencies (if needed)..."
if [[ -f package-lock.json ]]; then
  npm ci || npm install
else
  npm install
fi

echo "[run] Starting dev servers (frontend + API proxy)..."

# Ensure child processes are terminated on exit (Ctrl+C or script end)
cleanup() {
  echo "[run] Shutting down dev servers..."
  # Kill entire process group of this script
  pkill -P $$ || true
  # Also free ports in case processes detached
  free_port 5173 || true
  free_port 8787 || true
}
trap cleanup INT TERM EXIT

# Run in foreground so logs are visible; trap will handle cleanup
npm run dev
