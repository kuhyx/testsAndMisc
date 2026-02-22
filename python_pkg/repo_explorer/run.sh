#!/usr/bin/env bash
# Repo Explorer - browse and run any project in the monorepo via a GUI.
# Requires tkinter (Arch: sudo pacman -S python-tkinter)
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
VENV="$REPO_ROOT/.venv"

# Ensure tkinter is available (it's stdlib but needs the python-tkinter OS package)
if ! python3 -c "import tkinter" 2>/dev/null; then
    echo "tkinter not found. Installing python-tkinter..."
    sudo pacman -S --noconfirm python-tkinter 2>/dev/null \
        || sudo apt-get install -y python3-tk 2>/dev/null \
        || { echo "Please install python-tkinter manually."; exit 1; }
fi

[[ ! -d "$VENV" ]] && python3 -m venv "$VENV"
"$VENV/bin/python" "$SCRIPT_DIR/repo_explorer.py" "$@"
