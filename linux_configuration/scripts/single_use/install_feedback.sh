#!/usr/bin/env bash
# Install fee[dB]ack - open-source rhythm-gaming / music-education app with
# real-time note detection for guitar, bass, drums, keys, and vocals (WIP).
# https://got-feedback.org/
#
# fee[dB]ack has no AUR entry, so this builds a local-only pacman package
# from the PKGBUILD tracked alongside this script (feedback-appimage/), the
# same way hypersomnia-appimage/jackify-bin are installed on this machine.
#
# This script only BUILDS the package (no root needed). It prints the final
# `sudo pacman -U` command for you to run yourself, per policy: interactive
# sudo prompts are run by the user, not by an agent.
#
# Usage: ./install_feedback.sh

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info() { echo -e "${GREEN}[INFO]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PKGBUILD_SRC="$SCRIPT_DIR/feedback-appimage/PKGBUILD"

# ── Check prerequisites ─────────────────────────────────────────────
command -v pacman >/dev/null 2>&1 || {
	error "pacman not found. This script is for Arch Linux."
	exit 1
}
command -v makepkg >/dev/null 2>&1 || {
	error "makepkg not found (part of base-devel)."
	exit 1
}
[[ -f "$PKGBUILD_SRC" ]] || {
	error "PKGBUILD not found at $PKGBUILD_SRC"
	exit 1
}

if pacman -Qi feedback-appimage >/dev/null 2>&1; then
	info "feedback-appimage is already installed:"
	pacman -Qi feedback-appimage | grep -E '^(Name|Version|Install Date)'
	info "To reinstall/rebuild anyway, remove it first: sudo pacman -R feedback-appimage"
	exit 0
fi

# ── Build the package (no root required) ────────────────────────────
BUILD_DIR="$(mktemp -d)"
cleanup() { rm -rf "$BUILD_DIR"; }
trap cleanup EXIT

info "Building feedback-appimage in $BUILD_DIR..."
cp "$PKGBUILD_SRC" "$BUILD_DIR/PKGBUILD"
(cd "$BUILD_DIR" && makepkg --clean)

PKG_FILE=$(find "$BUILD_DIR" -maxdepth 1 -name 'feedback-appimage-*.pkg.tar.*' | head -1)
if [[ -z "$PKG_FILE" ]]; then
	error "Build finished but no package file was found in $BUILD_DIR"
	exit 1
fi

# Copy the built package out before the trap cleans up the build dir.
DEST="$SCRIPT_DIR/feedback-appimage/$(basename "$PKG_FILE")"
cp "$PKG_FILE" "$DEST"

echo ""
info "Built package: $DEST"
info "Install it by running:"
echo ""
echo "    sudo pacman -U '$DEST'"
echo ""
info "After installing: launch with 'feedback' (terminal) or via dmenu (fee[dB]ack)."
