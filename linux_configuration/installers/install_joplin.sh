#!/usr/bin/env bash
# Install Joplin - free, open-source, self-hostable note-taking app.
# Available on Linux (desktop), Android, iOS, Windows, macOS.
# Supports Markdown, end-to-end encryption, and self-hosted sync.
#
# This script:
#   1. Installs Joplin desktop app (AUR)
#   2. Optionally sets up Joplin Server via Docker for self-hosted sync
#
# Usage: ./install_joplin.sh [--with-server]
#
# Android app: https://play.google.com/store/apps/details?id=net.cozic.joplin
#              or via F-Droid

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info() { echo -e "${GREEN}[INFO]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

WITH_SERVER=false
JOPLIN_SERVER_PORT=22300
JOPLIN_DATA_DIR="$HOME/.joplin-server"
DUCKDNS_DOMAIN=""
DUCKDNS_TOKEN=""

for arg in "$@"; do
	case "$arg" in
	--with-server) WITH_SERVER=true ;;
	--help | -h)
		echo "Usage: $0 [--with-server]"
		echo ""
		echo "Options:"
		echo "  --with-server  Also set up Joplin Server via Docker"
		echo "  --help, -h     Show this help message"
		exit 0
		;;
	*)
		error "Unknown argument: $arg"
		exit 1
		;;
	esac
done

# ── Check prerequisites ─────────────────────────────────────────────
command -v pacman >/dev/null 2>&1 || {
	error "pacman not found. This script is for Arch Linux."
	exit 1
}

# ── Install Joplin Desktop ──────────────────────────────────────────
install_joplin_desktop() {
	if [[ -f "$HOME/.joplin/Joplin.AppImage" ]]; then
		info "Joplin desktop is already installed at $HOME/.joplin/Joplin.AppImage"
		return
	fi

	info "Installing Joplin desktop app via official installer (AppImage)..."

	# Official Joplin install script downloads the latest AppImage
	wget -O - https://raw.githubusercontent.com/laurent22/joplin/dev/Joplin_install_and_update.sh | bash

	info "Joplin desktop installed at ~/.joplin/Joplin.AppImage"
	info "Launch with: ~/.joplin/Joplin.AppImage  (or 'joplin-desktop' from menu)"
}

SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
# shellcheck source=joplin_server.sh
source "$SCRIPT_DIR/joplin_server.sh"

# ── Main ─────────────────────────────────────────────────────────────
main() {
	echo "╔══════════════════════════════════════════════╗"
	echo "║         Joplin Installation Script           ║"
	echo "║   Free & Open Source Note-Taking App         ║"
	echo "║   https://joplinapp.org                      ║"
	echo "╚══════════════════════════════════════════════╝"
	echo ""

	install_joplin_desktop

	if [[ "$WITH_SERVER" == true ]]; then
		setup_joplin_server
	else
		echo ""
		info "Tip: Run with --with-server to also set up Joplin Server"
		info "for self-hosted sync across devices (desktop + Android)."
	fi

	echo ""
	info "Android app available at:"
	info "  Google Play: https://play.google.com/store/apps/details?id=net.cozic.joplin"
	info "  F-Droid:     https://f-droid.org/packages/net.cozic.joplin/"
	echo ""
	info "Done!"
}

main
