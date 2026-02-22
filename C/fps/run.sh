#!/usr/bin/env bash
set -e
# Install dependencies
if command -v apt-get &>/dev/null; then
    sudo apt-get install -y freeglut3-dev libglu1-mesa-dev libsdl2-dev
elif command -v pacman &>/dev/null; then
    pacman -Q freeglut sdl2 &>/dev/null || sudo pacman -S --noconfirm freeglut sdl2
elif command -v dnf &>/dev/null; then
    sudo dnf install -y freeglut-devel mesa-libGLU-devel SDL2-devel
fi
make
./fps_demo
