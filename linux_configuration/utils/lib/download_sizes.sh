#!/bin/bash
# Size thresholds and the oversized-file moves.
#
# Sourced by organize_downloads.sh; split out to keep it under the 250-line cap.
# Sourced rather than run, so it inherits the caller's strict mode and
# the helper functions and variables defined above the source line.

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
