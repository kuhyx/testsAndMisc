#!/usr/bin/env bash
# Install Exercism CLI - Offline Coding Challenges
#
# Exercism is a free, open source platform with:
# - 65+ programming languages
# - Built-in test suites for each exercise
# - Works offline after downloading exercises
#
# Website: https://exercism.org
# License: AGPL-3.0

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

success() { echo -e "${GREEN}✓ $1${NC}"; }
warn() { echo -e "${YELLOW}⚠ $1${NC}"; }
error() { echo -e "${RED}✗ $1${NC}"; }
info() { echo -e "${BLUE}ℹ $1${NC}"; }

EXERCISM_DIR="${HOME}/exercism"

echo "=============================================="
echo " Exercism - Offline Coding Challenges"
echo " Free & Open Source with Built-in Tests"
echo "=============================================="
echo ""

# Install Exercism CLI
install_exercism_cli() {
	if command -v exercism &>/dev/null; then
		local version
		version=$(exercism version 2>/dev/null | head -1)
		success "Exercism CLI already installed: $version"
		return 0
	fi

	echo "Installing Exercism CLI..."

	# Try package managers first
	if command -v pacman &>/dev/null; then
		# Check AUR
		if command -v yay &>/dev/null; then
			yay -S --noconfirm exercism-bin
			success "Exercism CLI installed via AUR"
			return 0
		elif command -v paru &>/dev/null; then
			paru -S --noconfirm exercism-bin
			success "Exercism CLI installed via AUR"
			return 0
		fi
	elif command -v brew &>/dev/null; then
		brew install exercism
		success "Exercism CLI installed via Homebrew"
		return 0
	fi

	# Manual installation from GitHub releases
	info "Installing from GitHub releases..."

	local arch
	case "$(uname -m)" in
	x86_64) arch="x86_64" ;;
	aarch64 | arm64) arch="arm64" ;;
	armv7l) arch="armv7" ;;
	i686) arch="i386" ;;
	*)
		error "Unsupported architecture: $(uname -m)"
		return 1
		;;
	esac

	local os="linux"
	[[ "$(uname -s)" == "Darwin" ]] && os="darwin"

	# Get latest release
	local latest_url="https://api.github.com/repos/exercism/cli/releases/latest"
	local download_url

	download_url=$(curl -fsSL "$latest_url" | grep "browser_download_url.*${os}-${arch}" | head -1 | cut -d '"' -f 4)

	if [[ -z $download_url ]]; then
		error "Could not find download URL for your system"
		echo "Please install manually from: https://exercism.org/docs/using/solving-exercises/working-locally"
		return 1
	fi

	echo "Downloading from: $download_url"
	local temp_dir
	temp_dir=$(mktemp -d)

	curl -fL --progress-bar "$download_url" -o "$temp_dir/exercism.tar.gz"
	tar -xzf "$temp_dir/exercism.tar.gz" -C "$temp_dir"

	# Install to ~/.local/bin
	mkdir -p "$HOME/.local/bin"
	mv "$temp_dir/exercism" "$HOME/.local/bin/"
	chmod +x "$HOME/.local/bin/exercism"

	rm -rf "$temp_dir"

	success "Exercism CLI installed to ~/.local/bin/exercism"

	# Check PATH
	if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
		warn "Add ~/.local/bin to your PATH:"
		# Printing a line for the USER to paste into their shell rc: $HOME and
		# $PATH must appear literally, not be resolved to this machine's values.
		# shellcheck disable=SC2016
		echo '  export PATH="$HOME/.local/bin:$PATH"'
	fi
}

SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
# shellcheck source=lib/exercism_config.sh
source "$SCRIPT_DIR/lib/exercism_config.sh"

main() {
	# Step 1: Install CLI
	echo ""
	echo "=== Step 1: Installing Exercism CLI ==="
	install_exercism_cli

	# Step 2: Configure
	configure_exercism

	# Step 3: Install test runners
	install_test_runners

	# Step 4: Download sample exercises
	echo ""
	echo "=== Step 4: Downloading Sample Exercises ==="
	echo ""
	echo "Downloading a few starter exercises for common languages..."
	echo "(Full download requires API token from exercism.org)"
	echo ""

	# Try to download hello-world for each track
	local tracks=("python" "javascript" "typescript" "c" "cpp")

	for track in "${tracks[@]}"; do
		local exercise_dir="$EXERCISM_DIR/$track/hello-world"
		if [[ -d $exercise_dir ]]; then
			echo "  [$track] hello-world already exists"
		else
			if exercism download --track="$track" --exercise="hello-world" 2>/dev/null; then
				success "[$track] hello-world downloaded"
			else
				warn "[$track] hello-world requires authentication"
			fi
		fi
	done

	# Show usage
	show_usage

	echo ""
	success "Installation complete!"
	echo ""
	echo "Next steps:"
	echo "  1. Sign up at https://exercism.org (free)"
	echo "  2. Get your token from https://exercism.org/settings/api_cli"
	echo "  3. Run: exercism configure --token=YOUR_TOKEN"
	echo "  4. Download exercises and code offline!"
	echo ""
}

main "$@"
