#!/bin/bash
# Media-type classification for the download sweep.
#
# Sourced by organize_downloads.sh; split out to keep it under the 250-line cap.
# Sourced rather than run, so it inherits the caller's strict mode and
# the helper functions and variables defined above the source line.

# Function to check if file has media extension (zero forks: bash 4 ${var,,})
is_media_file() {
	local file="$1"
	local extension="${file##*.}"
	extension="${extension,,}"

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
