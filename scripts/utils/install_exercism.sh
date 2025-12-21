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

	if [[ -z "$download_url" ]]; then
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
		echo '  export PATH="$HOME/.local/bin:$PATH"'
	fi
}

# Configure exercism workspace
configure_exercism() {
	echo ""
	echo "=== Configuring Exercism ==="

	mkdir -p "$EXERCISM_DIR"

	# Check if already configured
	if exercism configure 2>&1 | grep -q "workspace"; then
		success "Exercism already configured"
	else
		# Set workspace directory
		exercism configure --workspace="$EXERCISM_DIR"
		success "Workspace set to: $EXERCISM_DIR"
	fi

	echo ""
	info "To fully configure Exercism with your account:"
	echo "  1. Create free account at https://exercism.org"
	echo "  2. Go to https://exercism.org/settings/api_cli"
	echo "  3. Copy your API token"
	echo "  4. Run: exercism configure --token=YOUR_TOKEN"
	echo ""
}

# Install test runners for languages
install_test_runners() {
	echo ""
	echo "=== Installing Test Runners ==="
	echo ""

	# Python - pytest
	if command -v python3 &>/dev/null; then
		if python3 -c "import pytest" 2>/dev/null; then
			success "Python: pytest already installed"
		else
			info "Installing pytest for Python exercises..."
			pip3 install --user pytest 2>/dev/null && success "Python: pytest installed" || warn "Python: install pytest manually"
		fi
	fi

	# JavaScript/TypeScript - Node.js + npm
	if command -v node &>/dev/null; then
		success "JavaScript/TypeScript: Node.js available ($(node --version))"
		info "  Tests run with: npm test (or jest)"
	else
		warn "JavaScript/TypeScript: Install Node.js for JS/TS exercises"
	fi

	# C - gcc + criterion/cmocka
	if command -v gcc &>/dev/null; then
		success "C: gcc available"
		info "  Some C exercises use Unity test framework (included in exercise)"
	else
		warn "C: Install gcc for C exercises"
	fi

	# C++ - g++ + Catch2/doctest
	if command -v g++ &>/dev/null; then
		success "C++: g++ available"
		info "  C++ exercises use Catch2 (header-only, included in exercise)"
	else
		warn "C++: Install g++ for C++ exercises"
	fi

	# Rust
	if command -v cargo &>/dev/null; then
		success "Rust: cargo available (tests with: cargo test)"
	fi

	# Go
	if command -v go &>/dev/null; then
		success "Go: go available (tests with: go test)"
	fi
}

# Download exercises for a track (language)
download_track() {
	local track="$1"
	local count="${2:-10}"

	echo ""
	info "Downloading $count exercises for $track track..."

	# Get list of exercises
	local exercises
	exercises=$(curl -fsSL "https://exercism.org/api/v2/tracks/${track}/exercises" 2>/dev/null |
		grep -oP '"slug":"\K[^"]+' | head -n "$count")

	if [[ -z "$exercises" ]]; then
		warn "Could not fetch exercise list for $track"
		return 1
	fi

	local downloaded=0
	for exercise in $exercises; do
		local exercise_dir="$EXERCISM_DIR/$track/$exercise"
		if [[ -d "$exercise_dir" ]]; then
			echo "  [exists] $exercise"
		else
			if exercism download --track="$track" --exercise="$exercise" 2>/dev/null; then
				echo "  [downloaded] $exercise"
				((downloaded++))
			else
				echo "  [failed] $exercise (may require auth)"
			fi
		fi
	done

	success "Downloaded $downloaded new exercises for $track"
}

# Show available tracks and usage
show_usage() {
	echo ""
	echo "=============================================="
	echo " Exercism Usage Guide"
	echo "=============================================="
	echo ""
	echo -e "${CYAN}Download exercises:${NC}"
	echo "  exercism download --track=python --exercise=hello-world"
	echo "  exercism download --track=javascript --exercise=two-fer"
	echo "  exercism download --track=c --exercise=isogram"
	echo ""
	echo -e "${CYAN}Run tests locally:${NC}"
	echo "  Python:      cd ~/exercism/python/hello-world && pytest"
	echo "  JavaScript:  cd ~/exercism/javascript/hello-world && npm test"
	echo "  TypeScript:  cd ~/exercism/typescript/hello-world && npm test"
	echo "  C:           cd ~/exercism/c/hello-world && make test"
	echo "  C++:         cd ~/exercism/cpp/hello-world && make"
	echo "  Rust:        cd ~/exercism/rust/hello-world && cargo test"
	echo "  Go:          cd ~/exercism/go/hello-world && go test"
	echo ""
	echo -e "${CYAN}Submit solution (when online):${NC}"
	echo "  exercism submit solution.py"
	echo ""
	echo -e "${CYAN}Popular tracks:${NC}"
	echo "  python, javascript, typescript, c, cpp, rust, go, java, ruby"
	echo "  bash, elixir, haskell, kotlin, swift, csharp, php, sql"
	echo ""
	echo -e "${CYAN}Batch download (requires API token):${NC}"
	echo "  # Download first 20 Python exercises:"
	echo "  for ex in \$(exercism download --track=python 2>&1 | head -20); do"
	echo "    exercism download --track=python --exercise=\$ex"
	echo "  done"
	echo ""
	echo "Exercises are in: $EXERCISM_DIR"
	echo ""
	echo "=============================================="
}

# Main
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
		if [[ -d "$exercise_dir" ]]; then
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
