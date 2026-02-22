#!/usr/bin/env bash
set -e
# Install dependencies
if command -v apt-get &>/dev/null; then
    sudo apt-get install -y libcurl4-openssl-dev libxml2-dev
elif command -v pacman &>/dev/null; then
    pacman -Q curl libxml2 &>/dev/null || sudo pacman -S --noconfirm curl libxml2
elif command -v dnf &>/dev/null; then
    sudo dnf install -y libcurl-devel libxml2-devel
fi
make
./scrape
