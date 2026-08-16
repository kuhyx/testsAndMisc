#!/bin/bash
# Media discovery, archiving and the per-category moves.
#
# Sourced by organize_downloads.sh; split out to keep it under the 250-line cap.
# Sourced rather than run, so it inherits the caller's strict mode and
# the helper functions and variables defined above the source line.

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
