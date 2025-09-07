#!/usr/bin/env bash
set -euo pipefail

# Run Mini Articles (backend + frontend) using the C server only
# Options (env): HOST (default 127.0.0.1), PORT (default 8000), ARTICLES_DATA_DIR

DIR=$(cd -- "$(dirname -- "$0")" && pwd)
SITE_DIR="$DIR"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"

start_server() {
  make -s -C "$SITE_DIR" server_c
  export HOST PORT ARTICLES_DATA_DIR
  "$SITE_DIR/server_c" &
  SRV_PID=$!
}

stop_server() {
  if [[ -n "${SRV_PID:-}" ]] && kill -0 "$SRV_PID" 2>/dev/null; then
    kill "$SRV_PID" 2>/dev/null || true
    wait "$SRV_PID" 2>/dev/null || true
  fi
}

restart_server() {
  echo "[watch] Rebuilding and restarting server_c..."
  stop_server
  start_server
}

open_browser_once() {
  local url="http://$HOST:$PORT/"
  if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$url" >/dev/null 2>&1 || true
  fi
  echo "Mini Articles running at $url"
}

start_server
trap 'stop_server' EXIT INT TERM

# Give it a moment to start
sleep 0.5
open_browser_once

echo "Press Ctrl+C to stop. Watching for changes in index.html and server_c.c (auto-reload enabled)..."

watch_poll() {
  local idx_mtime srv_mtime new_idx new_srv
  idx_mtime=$(stat -c %Y "$SITE_DIR/index.html" 2>/dev/null || echo 0)
  srv_mtime=$(stat -c %Y "$SITE_DIR/server_c.c" 2>/dev/null || echo 0)
  while true; do
    sleep 0.5
    new_idx=$(stat -c %Y "$SITE_DIR/index.html" 2>/dev/null || echo 0)
    new_srv=$(stat -c %Y "$SITE_DIR/server_c.c" 2>/dev/null || echo 0)
    if [[ "$new_srv" != "$srv_mtime" ]]; then
      srv_mtime="$new_srv"
      restart_server
    fi
    if [[ "$new_idx" != "$idx_mtime" ]]; then
      idx_mtime="$new_idx"
  echo "[watch] index.html changed. Browser will auto-reload."
    fi
  done
}

watch_inotify() {
  inotifywait -e close_write,create,move --format '%w%f' -m \
    "$SITE_DIR/index.html" "$SITE_DIR/server_c.c" | while read -r file; do
      case "$file" in
        *server_c.c) restart_server ;;
  *index.html) echo "[watch] index.html changed. Browser will auto-reload." ;;
      esac
    done
}

if command -v inotifywait >/dev/null 2>&1; then
  watch_inotify &
  WATCH_PID=$!
  wait "$WATCH_PID"
else
  watch_poll
fi
