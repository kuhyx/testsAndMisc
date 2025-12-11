#!/usr/bin/env bash

set -euo pipefail

# to_webm.sh
#
# Convert video files (non-webm) to webm format using ffmpeg.
# Accepts either a single video file or a directory (will recurse into subdirectories).

# Video extensions to search for (excluding webm since that's our target)
VIDEO_EXTENSIONS=("mp4" "mkv" "avi" "mov" "wmv" "flv" "m4v" "mpg" "mpeg" "3gp" "ogv" "ts" "mts" "m2ts" "vob" "asf" "rm" "rmvb" "divx" "f4v")

# Conversion settings
CRF=30          # Quality (0-63, lower = better quality, 23-30 is reasonable)
PRESET="medium" # Encoding speed: ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow
DELETE_ORIGINAL=false

log() {
	printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

usage() {
	cat <<EOF
Usage:
  $(basename "$0") [OPTIONS] PATH

Convert video files to webm format using ffmpeg.
PATH can be a single video file or a directory (will recurse into subdirectories).

Options:
  -c CRF       Quality level 0-63 (default: 30, lower = better quality)
  -p PRESET    Encoding preset (default: medium)
               Options: ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow
  -d           Delete original file after successful conversion
  -h           Show this help

Examples:
  $(basename "$0") video.mp4
  $(basename "$0") /path/to/videos/
  $(basename "$0") -c 25 -d /path/to/videos/
  $(basename "$0") -p slow -c 20 movie.mkv
EOF
}

ensure_ffmpeg() {
	if ! command -v ffmpeg >/dev/null 2>&1; then
		echo "Error: 'ffmpeg' is not installed or not in PATH." >&2
		exit 1
	fi
}

build_extension_pattern() {
	# Build a find pattern for video extensions
	local pattern=""
	for ext in "${VIDEO_EXTENSIONS[@]}"; do
		if [[ -n "$pattern" ]]; then
			pattern="$pattern -o"
		fi
		pattern="$pattern -iname *.$ext"
	done
	echo "$pattern"
}

is_video_file() {
	local file="$1"
	local ext="${file##*.}"
	ext="${ext,,}" # lowercase

	for video_ext in "${VIDEO_EXTENSIONS[@]}"; do
		if [[ "$ext" == "${video_ext,,}" ]]; then
			return 0
		fi
	done
	return 1
}

convert_to_webm() {
	local input_file="$1"
	local output_file="${input_file%.*}.webm"

	# Skip if output already exists
	if [[ -f "$output_file" ]]; then
		log "Skipping '$input_file': output '$output_file' already exists"
		return 0
	fi

	log "Converting '$input_file' -> '$output_file'"

	# Use VP9 codec for video and Opus for audio (good quality, wide compatibility)
	if ffmpeg -hide_banner -loglevel warning -i "$input_file" \
		-c:v libvpx-vp9 -crf "$CRF" -b:v 0 \
		-c:a libopus -b:a 128k \
		-preset "$PRESET" \
		"$output_file"; then
		log "Successfully converted '$input_file'"

		if [[ "$DELETE_ORIGINAL" == true ]]; then
			log "Deleting original: '$input_file'"
			rm "$input_file"
		fi
	else
		log "Error converting '$input_file'"
		# Remove partial output file if it exists
		[[ -f "$output_file" ]] && rm "$output_file"
		return 1
	fi
}

process_directory() {
	local dir="$1"
	local count=0
	local failed=0

	log "Searching for video files in '$dir'..."

	# Find all video files (case-insensitive)
	while IFS= read -r -d '' file; do
		# Skip webm files
		if [[ "${file,,}" == *.webm ]]; then
			continue
		fi

		((count++)) || true
		if ! convert_to_webm "$file"; then
			((failed++)) || true
		fi
	done < <(find "$dir" -type f \( -iname "*.mp4" -o -iname "*.mkv" -o -iname "*.avi" -o -iname "*.mov" \
		-o -iname "*.wmv" -o -iname "*.flv" -o -iname "*.m4v" -o -iname "*.mpg" -o -iname "*.mpeg" \
		-o -iname "*.3gp" -o -iname "*.ogv" -o -iname "*.ts" -o -iname "*.mts" -o -iname "*.m2ts" \
		-o -iname "*.vob" -o -iname "*.asf" -o -iname "*.rm" -o -iname "*.rmvb" -o -iname "*.divx" \
		-o -iname "*.f4v" \) -print0 2>/dev/null)

	log "Processed $count video file(s), $failed failed"

	if [[ $count -eq 0 ]]; then
		log "No video files found in '$dir'"
	fi
}

parse_args() {
	while getopts ":c:p:dh" opt; do
		case "$opt" in
		c) CRF="$OPTARG" ;;
		p) PRESET="$OPTARG" ;;
		d) DELETE_ORIGINAL=true ;;
		h)
			usage
			exit 0
			;;
		:)
			echo "Error: Option -$OPTARG requires an argument." >&2
			usage
			exit 1
			;;
		\?)
			echo "Error: Invalid option -$OPTARG" >&2
			usage
			exit 1
			;;
		esac
	done
	shift $((OPTIND - 1))

	if [[ $# -lt 1 ]]; then
		echo "Error: No path specified." >&2
		usage
		exit 1
	fi

	TARGET_PATH="$1"
}

main() {
	ensure_ffmpeg
	parse_args "$@"

	if [[ ! -e "$TARGET_PATH" ]]; then
		echo "Error: Path '$TARGET_PATH' does not exist." >&2
		exit 1
	fi

	if [[ -f "$TARGET_PATH" ]]; then
		# Single file
		if [[ "${TARGET_PATH,,}" == *.webm ]]; then
			log "File '$TARGET_PATH' is already in webm format, skipping."
			exit 0
		fi

		if is_video_file "$TARGET_PATH"; then
			convert_to_webm "$TARGET_PATH"
		else
			echo "Error: '$TARGET_PATH' is not a recognized video file." >&2
			exit 1
		fi
	elif [[ -d "$TARGET_PATH" ]]; then
		# Directory
		process_directory "$TARGET_PATH"
	else
		echo "Error: '$TARGET_PATH' is neither a file nor a directory." >&2
		exit 1
	fi

	log "Done!"
}

main "$@"
