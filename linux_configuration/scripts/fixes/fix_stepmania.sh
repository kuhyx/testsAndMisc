#!/usr/bin/env bash

# Fix StepMania AUR build failure due to missing vorbis libraries in linker
#
# Error addressed:
#   /usr/bin/ld: /usr/local/lib/libavcodec.a(libvorbisenc.o): undefined reference to symbol 'vorbis_encode_setup_vbr'
#   /usr/bin/ld: /usr/lib/libvorbisenc.so.2: error adding symbols: DSO missing from command line
#
# Cause:
#   Static libavcodec.a depends on libvorbisenc but cmake doesn't add it to linker flags
#
# Solution:
#   Add vorbis libraries to LDFLAGS before building
#
# Usage:
#   ./fix_stepmania.sh

set -euo pipefail

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
# shellcheck source=../lib/common.sh
source "$SCRIPT_DIR/../lib/common.sh"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }
log_success() { echo -e "${GREEN}[OK]${NC} $*"; }

check_dependencies() {
	log_info "Checking dependencies..."

	local missing=()

	# Check for vorbis libraries
	if ! pacman -Q libvorbis &>/dev/null; then
		missing+=("libvorbis")
	fi

	# Check for yay or paru
	if ! has_cmd yay && ! has_cmd paru; then
		log_error "Neither yay nor paru found. Please install an AUR helper."
		exit 1
	fi

	if [[ ${#missing[@]} -gt 0 ]]; then
		log_warn "Missing packages: ${missing[*]}"
		log_info "Installing missing dependencies..."
		sudo pacman -S --needed "${missing[@]}"
	else
		log_success "All dependencies present"
	fi
}

get_aur_helper() {
	if has_cmd yay; then
		echo "yay"
	elif has_cmd paru; then
		echo "paru"
	fi
}

build_stepmania() {
	local aur_helper
	aur_helper=$(get_aur_helper)

	log_info "Building StepMania with vorbis libraries in LDFLAGS..."
	log_info "Using AUR helper: $aur_helper"

	# Export LDFLAGS with vorbis libraries to fix the linking issue
	# The static libavcodec.a needs these shared libraries
	export LDFLAGS="${LDFLAGS:-} -lvorbis -lvorbisenc -lvorbisfile -logg"

	log_info "LDFLAGS set to: $LDFLAGS"

	# Clean any previous failed build
	if [[ -d "$HOME/.cache/$aur_helper/stepmania" ]]; then
		log_info "Cleaning previous build cache..."
		rm -rf "$HOME/.cache/$aur_helper/stepmania"
	fi

	# Build with the modified LDFLAGS
	# --noconfirm for non-interactive, --cleanafter to cleanup
	"$aur_helper" -S --rebuild --noconfirm stepmania

	log_success "StepMania built successfully!"
}

alternative_fix_info() {
	cat <<'EOF'

If the automated fix doesn't work, try these alternatives:

1. Use system ffmpeg instead of static libavcodec:
   - Edit the PKGBUILD to use shared ffmpeg libraries
   - Remove any bundled/static ffmpeg references

2. Manually edit CMakeLists.txt:
   - Find target_link_libraries for StepMania executable
   - Add: vorbis vorbisenc vorbisfile ogg

3. Check if /usr/local/lib/libavcodec.a is from a custom ffmpeg build:
   - If so, rebuild ffmpeg with --enable-shared or remove the static lib
   - System ffmpeg in /usr/lib should be preferred

4. Use the stepmania-git package instead which may have different build config

EOF
}

main() {
	echo "======================================"
	echo "  StepMania Build Fix"
	echo "======================================"
	echo ""

	check_dependencies
	echo ""

	log_info "This fix adds vorbis libraries to LDFLAGS to resolve:"
	log_info "  'undefined reference to symbol vorbis_encode_setup_vbr'"
	echo ""

	read -rp "Proceed with rebuild? [Y/n] " response
	case "$response" in
	[nN][oO] | [nN])
		log_info "Aborted."
		alternative_fix_info
		exit 0
		;;
	*)
		build_stepmania
		;;
	esac
}

main "$@"
