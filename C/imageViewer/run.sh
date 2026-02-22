#!/usr/bin/env bash
set -e
# Install dependencies
if command -v apt-get &>/dev/null; then
    sudo apt-get install -y libsdl2-dev libsdl2-image-dev
elif command -v pacman &>/dev/null; then
    pacman -Q sdl2 sdl2_image &>/dev/null || sudo pacman -S --noconfirm sdl2 sdl2_image
elif command -v dnf &>/dev/null; then
    sudo dnf install -y SDL2-devel SDL2_image-devel
fi
make
echo "Usage: ./imageviewer <image_file>"
if [[ $# -gt 0 ]]; then
    ./imageviewer "$@"
fi
