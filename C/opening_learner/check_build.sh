#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo "Checking for engine (stockfish or asmfish)"
if command -v stockfish >/dev/null 2>&1; then
  echo "Found stockfish"
elif command -v asmfish >/dev/null 2>&1; then
  echo "Found asmfish"
else
  echo "Error: Neither stockfish nor asmfish found in PATH." >&2
  exit 1
fi

echo "Checking for SDL2 dev (sdl2-config)"
if command -v sdl2-config >/dev/null 2>&1; then
  echo "Found sdl2-config"
else
  echo "Error: sdl2-config not found. Install SDL2 dev (e.g., libsdl2-dev)." >&2
  exit 2
fi

echo "Building project"
make clean
make -j

echo "Build OK"
