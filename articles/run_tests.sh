#!/usr/bin/env bash
set -euo pipefail

# Run only the website tests from this directory
DIR=$(cd -- "$(dirname -- "$0")" && pwd)
cd "$DIR"

PYTHON_BIN="${PYTHON:-}"
if [[ -z "${PYTHON_BIN}" ]]; then
  if command -v python >/dev/null 2>&1; then PYTHON_BIN=python
  elif command -v python3 >/dev/null 2>&1; then PYTHON_BIN=python3
  else
    echo "Python is required but not found in PATH." >&2
    exit 1
  fi
fi

# Be explicit to avoid collecting tests from other repo paths
"$PYTHON_BIN" -m pytest -q test_site_size.py test_server_api.py
