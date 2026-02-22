#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# pygame has no prebuilt wheel for Python 3.14+, use the system package
pacman -Q python-pygame &>/dev/null || sudo pacman -S --noconfirm python-pygame

# Use a local venv with --system-site-packages so it can see system pygame
VENV="$SCRIPT_DIR/.venv"
[[ ! -d "$VENV" ]] && python3 -m venv "$VENV" --system-site-packages
"$VENV/bin/python" "$SCRIPT_DIR/main.py" "$@"
