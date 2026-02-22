#!/usr/bin/env bash
set -e
# Install dependencies
if command -v apt-get &>/dev/null; then
    sudo apt-get install -y libjpeg-dev
elif command -v pacman &>/dev/null; then
    pacman -Q libjpeg-turbo &>/dev/null || sudo pacman -S --noconfirm libjpeg-turbo
elif command -v dnf &>/dev/null; then
    sudo dnf install -y libjpeg-turbo-devel
fi
make
./generate_images
