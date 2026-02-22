#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Use a local venv with pip-installed mitmproxy (not in Arch repos)
LVENV="$SCRIPT_DIR/.venv"
if [[ ! -d "$LVENV" ]]; then
    echo "Creating local venv for mitmproxy..."
    python3 -m venv "$LVENV"
fi
if ! "$LVENV/bin/python" -c "import mitmproxy" &>/dev/null; then
    echo "Installing mitmproxy..."
    "$LVENV/bin/pip" install mitmproxy -q
fi

cd "$SCRIPT_DIR"
"$LVENV/bin/mitmdump" --scripts mock_server.py "$@"
