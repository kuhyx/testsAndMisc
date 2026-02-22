#!/usr/bin/env bash
set -e
# Install dependencies
if command -v pacman &>/dev/null; then
    pacman -Q libwebsockets &>/dev/null || sudo pacman -S --noconfirm libwebsockets
elif command -v apt-get &>/dev/null; then
    sudo apt-get install -y libwebsockets-dev
elif command -v dnf &>/dev/null; then
    sudo dnf install -y libwebsockets-devel
elif command -v zypper &>/dev/null; then
    sudo zypper install -y libwebsockets-devel
else
    echo "Could not detect package manager. Please install libwebsockets manually." >&2
    exit 1
fi
make
./websocket_server
