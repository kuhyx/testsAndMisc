#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
VENV="$REPO_ROOT/.venv"
[[ ! -d "$VENV" ]] && python3 -m venv "$VENV"
_pip_sync() { local r="$1" h; h=$(md5sum "$r"|cut -d' ' -f1); local lf="$VENV/.req_${h:0:8}.lock"; [[ -f "$lf" ]] && return; "$VENV/bin/pip" install -r "$r" -q && touch "$lf"; }
_pip_sync "$SCRIPT_DIR/requirements.txt"
# Usage: ./run.sh <url> [--output-dir DIR] [--max-pages N]
"$VENV/bin/python" "$SCRIPT_DIR/scrape_comics.py" "$@"
