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

# Function to log messages with timestamp (bash builtin %()T = zero forks)
log() {
	local ts
	printf -v ts '%(%Y-%m-%d %H:%M:%S)T' -1
	echo "[$ts] $1"
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

SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
# shellcheck source=lib/download_classify.sh
source "$SCRIPT_DIR/lib/download_classify.sh"
# shellcheck source=lib/download_sizes.sh
source "$SCRIPT_DIR/lib/download_sizes.sh"
# shellcheck source=lib/download_media.sh
source "$SCRIPT_DIR/lib/download_media.sh"

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
