#!/bin/bash
# Exercism CLI configuration and per-track test runners.
#
# Sourced by install_exercism.sh; split out to keep it under the 250-line cap.
# Sourced rather than run, so it inherits the caller's strict mode and
# the helper functions and variables defined above the source line.

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
			if pip3 install --user pytest 2>/dev/null; then
				success "Python: pytest installed"
			else
				warn "Python: install pytest manually"
			fi
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

	if [[ -z $exercises ]]; then
		warn "Could not fetch exercise list for $track"
		return 1
	fi

	local downloaded=0
	for exercise in $exercises; do
		local exercise_dir="$EXERCISM_DIR/$track/$exercise"
		if [[ -d $exercise_dir ]]; then
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
	# Example commands printed for the user to copy; $(...) and $ex must stay
	# literal rather than execute here.
	# shellcheck disable=SC2016
	echo '  for ex in $(exercism download --track=python 2>&1 | head -20); do'
	# shellcheck disable=SC2016
	echo '    exercism download --track=python --exercise=$ex'
	echo "  done"
	echo ""
	echo "Exercises are in: $EXERCISM_DIR"
	echo ""
	echo "=============================================="
}

# Main
