#!/bin/bash
# Fix for "database AUR not found" error in yay
# This error occurs when yay's AUR database cache becomes corrupted
# or when using a buggy yay-git version

set -euo pipefail

echo "=== Fixing yay AUR database ==="

# Check if using yay-git (development version with potential bugs)
if pacman -Qi yay-git &> /dev/null; then
  echo ""
  echo "Detected yay-git (development version)."
  echo "The 'database AUR not found' error is a known bug in some yay-git versions."
  echo ""
  read -rp "Switch to stable yay? [Y/n] " response
  if [[ ${response,,} != "n" ]]; then
    echo "Switching to stable yay..."

    # Build and install stable yay from AUR
    TEMP_DIR=$(mktemp -d)
    cd "$TEMP_DIR"
    git clone https://aur.archlinux.org/yay.git
    cd yay

    # Remove yay-git and yay-git-debug (they conflict)
    sudo pacman -Rdd yay-git --noconfirm
    sudo pacman -Rdd yay-git-debug --noconfirm 2> /dev/null || true

    # Build and install stable yay
    makepkg -si --noconfirm

    cd /
    rm -rf "$TEMP_DIR"

    echo ""
    echo "=== Switched to stable yay ==="
    echo "You can now retry your yay command."
    exit 0
  fi
fi

# Remove yay's cache directory
YAY_CACHE_DIR="${HOME}/.cache/yay"
if [[ -d $YAY_CACHE_DIR ]]; then
  echo "Removing yay cache directory: $YAY_CACHE_DIR"
  rm -rf "$YAY_CACHE_DIR"
fi

# Remove yay's local database directory (stores AUR package info)
YAY_DB_DIR="${HOME}/.local/share/yay"
if [[ -d $YAY_DB_DIR ]]; then
  echo "Removing yay database directory: $YAY_DB_DIR"
  rm -rf "$YAY_DB_DIR"
fi

# Remove yay state directory
YAY_STATE_DIR="${HOME}/.local/state/yay"
if [[ -d $YAY_STATE_DIR ]]; then
  echo "Removing yay state directory: $YAY_STATE_DIR"
  rm -rf "$YAY_STATE_DIR"
fi

# Clear pacman's sync databases and refresh
echo "Refreshing pacman databases..."
sudo pacman -Sy

# Generate new yay database by running a simple query
echo "Regenerating yay AUR database..."
yay -Sy

echo ""
echo "=== Fix complete ==="
echo "You can now retry your yay command."
echo ""
echo "If the issue persists and you're using yay-git, consider running this script"
echo "again and choosing to switch to the stable yay version."
