#!/bin/bash

# Script to organize image and video files from Downloads and home directory
# Zips all media files with timestamp and removes originals
# Author: Generated for linux-configuration

# Set strict error handling
set -euo pipefail

# Defaults / flags
DRY_RUN=false
SAMPLE_LIMIT=20
# Size threshold for "too big" files (in bytes) - default 100MB
SIZE_THRESHOLD=$((100 * 1024 * 1024))

# Simple usage helper
usage() {
	cat <<EOF
Usage: $(basename "$0") [--dry-run|-n] [--sample=N]

Options:
    -n, --dry-run     Analyze and print what would be archived without creating a zip or removing files.
            --sample=N    In dry-run, show up to N sample file paths for select extensions (default: $SAMPLE_LIMIT).
    -h, --help        Show this help.
EOF
}

# Define directories to scan
DOWNLOADS_DIR="$HOME/Downloads"
HOME_DIR="$HOME"
TOO_BIG_DIR="$DOWNLOADS_DIR/too_big"
# Prefer a temp dir outside Downloads to avoid recursive re-inclusion; fall back to /tmp
TEMP_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/media_organize_$$"

# Define image and video file extensions
# Keep common raster/image formats; exclude svg/ico by default (often project assets), can be re-added if needed
IMAGE_EXTENSIONS=("jpg" "jpeg" "png" "gif" "bmp" "tiff" "tif" "webp" "raw" "cr2" "nef" "orf" "arw" "dng" "heic" "heif")
VIDEO_EXTENSIONS=("mp4" "avi" "mkv" "mov" "wmv" "flv" "webm" "m4v" "3gp" "ogv" "mpg" "mpeg" "mts" "m2ts" "vob")

# Function to log messages with timestamp
log() {
	echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Parse CLI flags early
while [[ ${1:-} =~ ^- ]]; do
	case "${1}" in
	-n | --dry-run)
		DRY_RUN=true
		shift
		;;
	--sample=*)
		SAMPLE_LIMIT="${1#*=}"
		shift
		;;
	-h | --help)
		usage
		exit 0
		;;
	*)
		echo "Unknown option: $1" >&2
		usage
		exit 1
		;;
	esac
done

# Function to check if file has media extension
is_media_file() {
	local file="$1"
	local extension="${file##*.}"
	extension=$(echo "$extension" | tr '[:upper:]' '[:lower:]')

	# Check if it's an image
	for ext in "${IMAGE_EXTENSIONS[@]}"; do
		if [[ $extension == "$ext" ]]; then
			return 0
		fi
	done

	# Check if it's a video
	for ext in "${VIDEO_EXTENSIONS[@]}"; do
		if [[ $extension == "$ext" ]]; then
			return 0
		fi
	done

	return 1
}

# Function to check if file is too big for archiving
is_too_big() {
	local file="$1"
	local size
	size=$(stat -c%s "$file" 2>/dev/null || echo "0")
	[[ $size -gt $SIZE_THRESHOLD ]]
}

# Function to move oversized files to too_big directory
move_big_files() {
	local files=("$@")
	local moved_count=0

	if [[ ${#files[@]} -eq 0 ]]; then
		return 0
	fi

	# Create too_big directory if it doesn't exist
	mkdir -p "$TOO_BIG_DIR"

	log "Moving ${#files[@]} oversized files to $TOO_BIG_DIR..."

	for file in "${files[@]}"; do
		if [[ -f $file ]]; then
			local basename
			basename=$(basename "$file")
			local dest="$TOO_BIG_DIR/$basename"

			# Handle filename collision
			if [[ -f $dest ]]; then
				local timestamp
				timestamp=$(date '+%Y%m%d_%H%M%S')
				local name="${basename%.*}"
				local ext="${basename##*.}"
				if [[ $name == "$ext" ]]; then
					dest="$TOO_BIG_DIR/${name}_${timestamp}"
				else
					dest="$TOO_BIG_DIR/${name}_${timestamp}.${ext}"
				fi
			fi

			if mv "$file" "$dest" 2>/dev/null; then
				log "Moved (too big): $(basename "$file") -> $dest"
				moved_count=$((moved_count + 1))
			else
				log "ERROR: Failed to move $(basename "$file")"
			fi
		fi
	done

	log "Successfully moved $moved_count oversized files."
}

# Function to find media files in a directory (non-recursive for home, avoid common system dirs)
find_media_files() {
	local search_dir="$1"
	local files=()
	# Directories to exclude under Downloads
	local -a EXCLUDES=(
		".git" ".hg" ".svn" ".cache" "node_modules" "dist" "build" "out" "target" "coverage" "__pycache__" "venv" ".venv"
		# previous staging dirs created by this script
		".media_organize_" "media_organize_"
		# too_big folder for oversized files
		"too_big"
	)

	if [[ $search_dir == "$HOME_DIR" ]]; then
		# For home directory, only check files directly in ~ (not subdirectories)
		# Exclude common system/config directories
		while IFS= read -r -d '' file; do
			local basename
			basename=$(basename "$file")
			# Skip hidden files and common system directories
			if [[ ! $basename =~ ^\. ]] && [[ -f $file ]]; then
				if is_media_file "$file"; then
					files+=("$file")
				fi
			fi
		done < <(find "$search_dir" -maxdepth 1 -type f -print0 2>/dev/null)
	else
		# For Downloads, search recursively, pruning excluded directories
		# Build prune expression
		local prune_expr=()
		for ex in "${EXCLUDES[@]}"; do
			prune_expr+=(-name "$ex*" -o)
		done
		# Remove trailing -o
		unset 'prune_expr[${#prune_expr[@]}-1]'

		while IFS= read -r -d '' file; do
			if is_media_file "$file"; then
				files+=("$file")
			fi
		done < <(find "$search_dir" \( -type d \( "${prune_expr[@]}" \) -prune \) -o -type f -print0 2>/dev/null)
	fi

	printf '%s\n' "${files[@]}"
}

# Function to create timestamped zip archive
create_media_archive() {
	local files=("$@")

	if [[ ${#files[@]} -eq 0 ]]; then
		log "No media files found to archive."
		return 0
	fi

	# Create timestamp for archive name
	local timestamp
	timestamp=$(date '+%Y%m%d_%H%M%S')
	local archive_name="media_archive_${timestamp}.zip"
	local archive_path="$DOWNLOADS_DIR/$archive_name"

	# Create temporary directory (fallback to /tmp if needed)
	if ! mkdir -p "$TEMP_DIR" 2>/dev/null; then
		TEMP_DIR="/tmp/media_organize_$$"
		mkdir -p "$TEMP_DIR"
	fi

	# Ensure temp dir is cleaned up on function return; trap unsets itself after running
	trap 'rm -rf "$TEMP_DIR" 2>/dev/null || true; trap - RETURN' RETURN

	log "Found ${#files[@]} media files to archive."
	log "Creating archive: $archive_path"

	# Copy files to temp directory maintaining relative structure
	local successfully_copied=()
	local copy_errors=0

	for file in "${files[@]}"; do
		if [[ -f $file ]]; then
			local relative_path=""
			if [[ $file == "$DOWNLOADS_DIR"* ]]; then
				relative_path="downloads/${file#"$DOWNLOADS_DIR"/}"
			else
				relative_path="home/${file#"$HOME_DIR"/}"
			fi

			local temp_file="$TEMP_DIR/$relative_path"
			local temp_dir
			temp_dir=$(dirname "$temp_file")

			mkdir -p "$temp_dir"
			# Check readability first to provide a clearer error
			if [[ ! -r $file ]]; then
				log "WARNING: Cannot read $file (permission denied?)"
				((copy_errors++)) || true
				continue
			fi

			# Attempt copy and capture any error for logging
			local cp_err
			if cp_err=$(cp -p "$file" "$temp_file" 2>&1); then
				successfully_copied+=("$file")
			else
				# Surface the cp error so the user can see the reason
				log "WARNING: Failed to copy $file -> $cp_err"
				# Special hint for space issues
				if echo "$cp_err" | grep -qi "No space left on device"; then
					log "HINT: Not enough free space to stage files. Using $TEMP_DIR. Free up space or change TEMP_DIR."
				fi
				((copy_errors++)) || true
			fi
		fi
	done

	if [[ ${#successfully_copied[@]} -eq 0 ]]; then
		log "ERROR: No files were successfully copied to temp directory."
		rm -rf "$TEMP_DIR"
		return 1
	fi

	if [[ $copy_errors -gt 0 ]]; then
		log "WARNING: $copy_errors files failed to copy."
	fi

	# Create zip archive with maximum compression
	log "Creating zip archive with ${#successfully_copied[@]} files..."
	cd "$TEMP_DIR"
	if zip -9 -r "$archive_path" . 2>&1; then
		log "Successfully created archive with ${#successfully_copied[@]} files."

		# Verify the zip file was actually created and is not empty
		if [[ ! -f $archive_path ]]; then
			log "ERROR: Archive file was not created at $archive_path"
			rm -rf "$TEMP_DIR"
			return 1
		fi

		local archive_size
		archive_size=$(stat -c%s "$archive_path" 2>/dev/null || echo "0")
		if [[ $archive_size -eq 0 ]]; then
			log "ERROR: Archive file is empty"
			rm -rf "$TEMP_DIR"
			return 1
		fi

		# Remove original files only if zip was successful
		local removed_count=0
		local remove_errors=0

		log "Starting to remove ${#successfully_copied[@]} original files..."

		# Temporarily disable strict error handling for file removal
		set +e

		for file in "${successfully_copied[@]}"; do
			if [[ -f $file ]]; then
				if rm "$file" 2>/dev/null; then
					removed_count=$((removed_count + 1))
					log "Removed: $(basename "$file")"
				else
					remove_errors=$((remove_errors + 1))
					log "ERROR: Failed to remove $(basename "$file")"
				fi
			else
				log "WARNING: File no longer exists: $(basename "$file")"
			fi
		done

		# Re-enable strict error handling
		set -e

		log "Successfully removed $removed_count original files."
		if [[ $remove_errors -gt 0 ]]; then
			log "WARNING: Failed to remove $remove_errors files."
		fi
		log "Archive size: $(du -h "$archive_path" | cut -f1)"

		# Cleanup temp directory (trap will also attempt, which is safe)
		rm -rf "$TEMP_DIR"

		# Return success only if we removed files or there were no files to remove
		if [[ $removed_count -gt 0 ]] || [[ ${#successfully_copied[@]} -eq 0 ]]; then
			return 0
		else
			log "ERROR: Failed to remove any files after successful archive creation."
			return 1
		fi
	else
		log "ERROR: Failed to create archive. Original files preserved."
		log "Zip command failed."
		rm -rf "$TEMP_DIR"
		return 1
	fi
}

# Main execution
main() {
	log "Starting media file organization..."

	# Check if required directories exist
	if [[ ! -d $DOWNLOADS_DIR ]]; then
		log "ERROR: Downloads directory not found: $DOWNLOADS_DIR"
		exit 1
	fi

	if [[ ! -d $HOME_DIR ]]; then
		log "ERROR: Home directory not found: $HOME_DIR"
		exit 1
	fi

	# Check if zip command is available
	if ! command -v zip >/dev/null 2>&1; then
		log "ERROR: zip command not found. Please install zip package."
		exit 1
	fi

	# Find all media files
	log "Scanning for media files..."
	local all_files=()

	# Find files in Downloads directory
	log "Scanning Downloads directory..."
	while IFS= read -r file; do
		[[ -n $file ]] && all_files+=("$file")
	done < <(find_media_files "$DOWNLOADS_DIR")

	# Find files in home directory (only direct files, not subdirectories)
	log "Scanning home directory (root level only)..."
	while IFS= read -r file; do
		[[ -n $file ]] && all_files+=("$file")
	done < <(find_media_files "$HOME_DIR")

	if $DRY_RUN; then
		log "Dry-run mode: summarizing what would be archived."
		if [[ ${#all_files[@]} -eq 0 ]]; then
			log "No media files found to organize."
			exit 0
		fi

		# Separate big files for dry-run reporting
		local dry_regular_files=()
		local dry_big_files=()
		for f in "${all_files[@]}"; do
			if is_too_big "$f"; then
				dry_big_files+=("$f")
			else
				dry_regular_files+=("$f")
			fi
		done

		# Count by extension
		declare -A ext_counts=()
		# Count by top-level directory under Downloads
		declare -A dir_counts=()
		# Sample paths for suspect extensions
		declare -A samples_ts=()
		declare -A samples_svg=()
		declare -A samples_ico=()

		for f in "${all_files[@]}"; do
			# Extension
			ext="${f##*.}"
			ext="${ext,,}"
			((ext_counts["$ext"]++)) || true

			# Top directory under Downloads
			if [[ $f == "$DOWNLOADS_DIR"/* ]]; then
				rel="${f#"$DOWNLOADS_DIR"/}"
				topdir="${rel%%/*}"
				[[ $topdir == "$rel" ]] && topdir="."
				((dir_counts["$topdir"]++)) || true
			else
				((dir_counts["~"]++)) || true
			fi

			# Samples for suspect extensions
			case "$ext" in
			ts)
				if [[ ${#samples_ts[@]} -lt $SAMPLE_LIMIT ]]; then samples_ts["$f"]=1; fi
				;;
			svg)
				if [[ ${#samples_svg[@]} -lt $SAMPLE_LIMIT ]]; then samples_svg["$f"]=1; fi
				;;
			ico)
				if [[ ${#samples_ico[@]} -lt $SAMPLE_LIMIT ]]; then samples_ico["$f"]=1; fi
				;;
			esac
		done

		echo ""
		echo "Summary by extension (top 20):"
		for k in "${!ext_counts[@]}"; do
			printf "%8d %s\n" "${ext_counts[$k]}" "$k"
		done | sort -nr | head -n 20

		echo ""
		echo "Top contributing directories under Downloads (top 20):"
		for k in "${!dir_counts[@]}"; do
			printf "%8d %s\n" "${dir_counts[$k]}" "$k"
		done | sort -nr | head -n 20

		echo ""
		if [[ ${#samples_ts[@]} -gt 0 ]]; then
			echo "Sample .ts files (TypeScript vs Transport Stream) up to $SAMPLE_LIMIT:"
			for p in "${!samples_ts[@]}"; do echo "  $p"; done | sort
			echo ""
		fi
		if [[ ${#samples_svg[@]} -gt 0 ]]; then
			echo "Sample .svg files up to $SAMPLE_LIMIT:"
			for p in "${!samples_svg[@]}"; do echo "  $p"; done | sort
			echo ""
		fi
		if [[ ${#samples_ico[@]} -gt 0 ]]; then
			echo "Sample .ico files up to $SAMPLE_LIMIT:"
			for p in "${!samples_ico[@]}"; do echo "  $p"; done | sort
			echo ""
		fi

		echo "Files to archive (regular size): ${#dry_regular_files[@]}"
		echo "Files to move to too_big folder: ${#dry_big_files[@]}"
		if [[ ${#dry_big_files[@]} -gt 0 ]]; then
			echo ""
			echo "Oversized files (> $((SIZE_THRESHOLD / 1024 / 1024))MB) that would be moved to too_big/:"
			for f in "${dry_big_files[@]}"; do
				local size
				size=$(du -h "$f" 2>/dev/null | cut -f1)
				echo "  [$size] $f"
			done | head -n "$SAMPLE_LIMIT"
			if [[ ${#dry_big_files[@]} -gt $SAMPLE_LIMIT ]]; then
				echo "  ... and $((${#dry_big_files[@]} - SAMPLE_LIMIT)) more"
			fi
		fi
		echo ""
		echo "Total files that would be organized: ${#all_files[@]}"
		echo "(Use: $(basename "$0") --dry-run --sample=50 to see more examples.)"
		exit 0
	fi

	# Separate files into regular and too-big categories
	local regular_files=()
	local big_files=()

	for file in "${all_files[@]}"; do
		if is_too_big "$file"; then
			big_files+=("$file")
		else
			regular_files+=("$file")
		fi
	done

	log "Found ${#regular_files[@]} regular files and ${#big_files[@]} oversized files."

	# Move oversized files to too_big directory
	if [[ ${#big_files[@]} -gt 0 ]]; then
		move_big_files "${big_files[@]}"
	fi

	# Create archive for regular-sized files
	if [[ ${#regular_files[@]} -gt 0 ]]; then
		create_media_archive "${regular_files[@]}"
		log "Media organization completed successfully."
	else
		log "No regular-sized media files found to archive."
	fi
}

# Run main function
main "$@"
