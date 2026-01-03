#!/bin/bash
# Find all KeePassXC database files (.kdbx) on the system and move them to a single location
# Uses 'fd' for fast searching - install with: sudo pacman -S fd
#
# Usage: ./find_keepassxc.sh [destination_directory]
# Default destination: ~/Keepass

set -euo pipefail

# Source common library if available
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
if [[ -f "$SCRIPT_DIR/../lib/common.sh" ]]; then
	# shellcheck source=../lib/common.sh
	source "$SCRIPT_DIR/../lib/common.sh"
else
	log() { printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }
fi

# Configuration
DEST_DIR="${1:-$HOME/Keepass}"
SEARCH_ROOT="/"
TIMEOUT_SECONDS=30

# Ensure fd is installed
if ! command -v fd &>/dev/null; then
	log "ERROR: 'fd' is not installed. Install with: sudo pacman -S fd"
	exit 1
fi

# Create destination directory if it doesn't exist
mkdir -p "$DEST_DIR"
log "Destination directory: $DEST_DIR"

# Find all .kdbx files using fd (very fast, respects .gitignore by default, but we use -u for unrestricted)
# -e kdbx: search by extension
# -u: unrestricted (include hidden and ignored files)
# -a: absolute paths
# --one-file-system: don't cross filesystem boundaries (optional, remove if you want to search mounted drives)
log "Searching for .kdbx files across the system (timeout: ${TIMEOUT_SECONDS}s)..."

# Use timeout to ensure the search doesn't take too long
# Exclude /proc, /sys, /dev, /run, /tmp, /var/cache, /var/tmp for speed
FOUND_FILES=$(timeout "$TIMEOUT_SECONDS" fd \
	-e kdbx \
	-u \
	-a \
	--exclude '/proc' \
	--exclude '/sys' \
	--exclude '/dev' \
	--exclude '/run' \
	--exclude '/tmp' \
	--exclude '/var/cache' \
	--exclude '/var/tmp' \
	--exclude '/snap' \
	--exclude '/.snapshots' \
	--exclude '/lost+found' \
	. "$SEARCH_ROOT" 2>/dev/null || true)

if [[ -z "$FOUND_FILES" ]]; then
	log "No .kdbx files found."
	exit 0
fi

# Count and display found files
FILE_COUNT=$(echo "$FOUND_FILES" | wc -l)
log "Found $FILE_COUNT .kdbx file(s):"
echo "$FOUND_FILES" | while read -r file; do
	echo "  - $file"
done

# Move files to destination
log "Moving files to $DEST_DIR..."
MOVED_COUNT=0
SKIPPED_COUNT=0

while IFS= read -r src_file; do
	[[ -z "$src_file" ]] && continue

	# Skip if file is already in destination
	if [[ "$(dirname "$src_file")" == "$DEST_DIR" ]]; then
		log "Skipping (already in destination): $src_file"
		((SKIPPED_COUNT++)) || true
		continue
	fi

	# Get the base filename
	base_name=$(basename "$src_file")
	dest_file="$DEST_DIR/$base_name"

	# Handle filename conflicts by adding a number suffix
	if [[ -f "$dest_file" ]]; then
		# Check if it's the exact same file (by content)
		if cmp -s "$src_file" "$dest_file"; then
			log "Skipping (identical file exists): $src_file"
			# Remove the duplicate source file
			rm -v "$src_file"
			((SKIPPED_COUNT++)) || true
			continue
		fi

		# Different file with same name - add suffix
		counter=1
		name_without_ext="${base_name%.kdbx}"
		while [[ -f "$dest_file" ]]; do
			dest_file="$DEST_DIR/${name_without_ext} ($counter).kdbx"
			((counter++))
		done
		log "Renaming to avoid conflict: $base_name -> $(basename "$dest_file")"
	fi

	# Move the file
	if mv -v "$src_file" "$dest_file"; then
		((MOVED_COUNT++)) || true
	else
		log "ERROR: Failed to move $src_file"
	fi
done <<<"$FOUND_FILES"

log "Done! Moved $MOVED_COUNT file(s), skipped $SKIPPED_COUNT file(s)."
log "All KeePassXC databases are now in: $DEST_DIR"

# List final contents
log "Contents of $DEST_DIR:"
ls -la "$DEST_DIR"/*.kdbx 2>/dev/null || log "No .kdbx files in destination"
