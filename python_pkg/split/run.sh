#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"$SCRIPT_DIR/../../.venv/bin/python" "$SCRIPT_DIR/split_x_into_n_symmetrically.py" "$@"
