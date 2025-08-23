#!/usr/bin/env bash

set -euo pipefail

# Directory of this script (lichess_bot module root)
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

# Try to detect repo root (two levels up from PYTHON/lichess_bot)
REPO_ROOT="$(cd "$ROOT_DIR/../.." 2>/dev/null && pwd)"

# Prefer Python 3 if available
if command -v python3 >/dev/null 2>&1; then
  PY=python3
else
  PY=python
fi

echo "[run_tests] Base Python: $($PY -c 'import sys; print(sys.executable)')"

# Create/use local virtual environment to avoid system-managed pip restrictions (PEP 668)
VENV_DIR="$ROOT_DIR/.venv"
if [[ ! -d "$VENV_DIR" ]]; then
  echo "[run_tests] Creating virtual environment at $VENV_DIR"
  $PY -m venv "$VENV_DIR"
fi

VENV_PY="$VENV_DIR/bin/python"
echo "[run_tests] Venv Python: $($VENV_PY -c 'import sys; print(sys.executable)')"

echo "[run_tests] Upgrading pip/setuptools/wheel"
"$VENV_PY" -m pip install --upgrade pip setuptools wheel >/dev/null

# Choose requirements file: prefer repo root, fallback to local
REQ_FILE=""
if [[ -f "$REPO_ROOT/requirements.txt" ]]; then
  REQ_FILE="$REPO_ROOT/requirements.txt"
elif [[ -f "$ROOT_DIR/requirements.txt" ]]; then
  REQ_FILE="$ROOT_DIR/requirements.txt"
fi

if [[ -n "$REQ_FILE" ]]; then
  echo "[run_tests] Installing requirements from $REQ_FILE"
  "$VENV_PY" -m pip install -r "$REQ_FILE"
else
  echo "[run_tests] No requirements.txt found; proceeding without dependency install"
fi

# Ensure pytest is available in venv
if ! "$VENV_PY" -c "import pytest" >/dev/null 2>&1; then
  echo "[run_tests] Installing pytest"
  "$VENV_PY" -m pip install pytest
fi

# Make project importable (module root and repo root)
export PYTHONPATH="$ROOT_DIR:${REPO_ROOT:-$ROOT_DIR}:${PYTHONPATH:-}"

TEST_PATH_REL="PYTHON/lichess_bot/tests"
TEST_PATH_ABS="$REPO_ROOT/$TEST_PATH_REL"
if [[ ! -d "$TEST_PATH_ABS" ]]; then
  # Fallback if script moved and relative layout differs
  if [[ -d "$ROOT_DIR/tests" ]]; then
    TEST_PATH_ABS="$ROOT_DIR/tests"
  else
    echo "[run_tests] Test directory not found (tried: $TEST_PATH_ABS and $ROOT_DIR/tests)." >&2
    exit 1
  fi
fi

echo "[run_tests] Running pytest for $TEST_PATH_ABS"
"$VENV_PY" -m pytest -q "$TEST_PATH_ABS" "$@"
