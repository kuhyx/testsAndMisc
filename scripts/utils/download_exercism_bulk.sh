#!/usr/bin/env bash
# Download ALL Exercism exercises for offline practice
#
# This clones the official Exercism track repositories which contain
# ALL exercises with their test suites - no need to unlock one by one!
#
# Exercises are in: exercises/practice/<exercise-name>/
# Each exercise has tests you can run locally.

set -euo pipefail

TRACKS_DIR="${HOME}/exercism-tracks"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

success() { echo -e "${GREEN}✓ $1${NC}"; }
info() { echo -e "${BLUE}ℹ $1${NC}"; }
warn() { echo -e "${YELLOW}⚠ $1${NC}"; }

echo "=============================================="
echo " Exercism Bulk Exercise Downloader"
echo " Download ALL exercises for offline practice"
echo "=============================================="
echo ""

mkdir -p "$TRACKS_DIR"
cd "$TRACKS_DIR"

# Tracks to download (add/remove as needed)
declare -A TRACKS=(
	["python"]="https://github.com/exercism/python.git"
	["c"]="https://github.com/exercism/c.git"
	["cpp"]="https://github.com/exercism/cpp.git"
	["javascript"]="https://github.com/exercism/javascript.git"
	["typescript"]="https://github.com/exercism/typescript.git"
	["rust"]="https://github.com/exercism/rust.git"
	["go"]="https://github.com/exercism/go.git"
	["bash"]="https://github.com/exercism/bash.git"
)

# Optional tracks (uncomment to include)
# TRACKS["java"]="https://github.com/exercism/java.git"
# TRACKS["ruby"]="https://github.com/exercism/ruby.git"
# TRACKS["haskell"]="https://github.com/exercism/haskell.git"
# TRACKS["elixir"]="https://github.com/exercism/elixir.git"

echo "Downloading ${#TRACKS[@]} tracks to: $TRACKS_DIR"
echo ""

for track in "${!TRACKS[@]}"; do
	url="${TRACKS[$track]}"

	if [[ -d "$track" ]]; then
		info "Updating $track..."
		(cd "$track" && git pull --quiet) && success "$track updated"
	else
		info "Cloning $track..."
		git clone --depth 1 "$url" && success "$track cloned"
	fi

	# Show exercise count
	if [[ -d "$track/exercises/practice" ]]; then
		count=$(ls "$track/exercises/practice" | wc -l)
		echo "    → $count practice exercises available"
	fi
	echo ""
done

echo "=============================================="
echo " Download Complete!"
echo "=============================================="
echo ""
echo "Exercises location: $TRACKS_DIR/<track>/exercises/practice/"
echo ""
echo "Example - Running Python exercises:"
echo "  cd $TRACKS_DIR/python/exercises/practice/hello-world"
echo "  python -m pytest -v"
echo ""
echo "Example - Running C exercises:"
echo "  cd $TRACKS_DIR/c/exercises/practice/hello-world"
echo "  make test"
echo ""
echo "Example - Running JavaScript exercises:"
echo "  cd $TRACKS_DIR/javascript/exercises/practice/hello-world"
echo "  npm install && npm test"
echo ""
echo "Each exercise folder contains:"
echo "  - README.md       (instructions)"
echo "  - *_test.*        (test file - run these!)"
echo "  - .meta/exemplar.* (reference solution - don't peek!)"
echo ""
echo "=============================================="

# Summary
echo ""
echo "Track summary:"
for track in "${!TRACKS[@]}"; do
	if [[ -d "$track/exercises/practice" ]]; then
		count=$(ls "$track/exercises/practice" 2>/dev/null | wc -l)
		printf "  %-15s %3d exercises\n" "$track" "$count"
	fi
done | sort
