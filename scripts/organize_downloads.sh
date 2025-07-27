#!/bin/bash

# Script to organize image and video files from Downloads and home directory
# Zips all media files with timestamp and removes originals
# Author: Generated for linux-configuration

# Set strict error handling
set -euo pipefail

# Define directories to scan
DOWNLOADS_DIR="$HOME/Downloads"
HOME_DIR="$HOME"
TEMP_DIR="/tmp/media_organize_$$"

# Define image and video file extensions
IMAGE_EXTENSIONS=("jpg" "jpeg" "png" "gif" "bmp" "tiff" "tif" "webp" "svg" "ico" "raw" "cr2" "nef" "orf" "arw" "dng" "heic" "heif")
VIDEO_EXTENSIONS=("mp4" "avi" "mkv" "mov" "wmv" "flv" "webm" "m4v" "3gp" "ogv" "mpg" "mpeg" "ts" "mts" "m2ts" "vob")

# Function to log messages with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Function to check if file has media extension
is_media_file() {
    local file="$1"
    local extension="${file##*.}"
    extension=$(echo "$extension" | tr '[:upper:]' '[:lower:]')
    
    # Check if it's an image
    for ext in "${IMAGE_EXTENSIONS[@]}"; do
        if [[ "$extension" == "$ext" ]]; then
            return 0
        fi
    done
    
    # Check if it's a video
    for ext in "${VIDEO_EXTENSIONS[@]}"; do
        if [[ "$extension" == "$ext" ]]; then
            return 0
        fi
    done
    
    return 1
}

# Function to find media files in a directory (non-recursive for home, avoid common system dirs)
find_media_files() {
    local search_dir="$1"
    local files=()
    
    if [[ "$search_dir" == "$HOME_DIR" ]]; then
        # For home directory, only check files directly in ~ (not subdirectories)
        # Exclude common system/config directories
        while IFS= read -r -d '' file; do
            local basename=$(basename "$file")
            # Skip hidden files and common system directories
            if [[ ! "$basename" =~ ^\. ]] && [[ -f "$file" ]]; then
                if is_media_file "$file"; then
                    files+=("$file")
                fi
            fi
        done < <(find "$search_dir" -maxdepth 1 -type f -print0 2>/dev/null)
    else
        # For Downloads, search recursively
        while IFS= read -r -d '' file; do
            if is_media_file "$file"; then
                files+=("$file")
            fi
        done < <(find "$search_dir" -type f -print0 2>/dev/null)
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
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    local archive_name="media_archive_${timestamp}.zip"
    local archive_path="$DOWNLOADS_DIR/$archive_name"
    
    # Create temporary directory
    mkdir -p "$TEMP_DIR"
    
    log "Found ${#files[@]} media files to archive."
    log "Creating archive: $archive_path"
    
    # Copy files to temp directory maintaining relative structure
    local successfully_copied=()
    local copy_errors=0
    
    for file in "${files[@]}"; do
        if [[ -f "$file" ]]; then
            local relative_path=""
            if [[ "$file" == "$DOWNLOADS_DIR"* ]]; then
                relative_path="downloads/${file#$DOWNLOADS_DIR/}"
            else
                relative_path="home/${file#$HOME_DIR/}"
            fi
            
            local temp_file="$TEMP_DIR/$relative_path"
            local temp_dir=$(dirname "$temp_file")
            
            mkdir -p "$temp_dir"
            if cp "$file" "$temp_file" 2>/dev/null; then
                successfully_copied+=("$file")
            else
                log "WARNING: Failed to copy $file"
                ((copy_errors++))
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
        if [[ ! -f "$archive_path" ]]; then
            log "ERROR: Archive file was not created at $archive_path"
            rm -rf "$TEMP_DIR"
            return 1
        fi
        
        local archive_size=$(stat -c%s "$archive_path" 2>/dev/null || echo "0")
        if [[ "$archive_size" -eq 0 ]]; then
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
            if [[ -f "$file" ]]; then
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
        
        # Cleanup temp directory
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
    if [[ ! -d "$DOWNLOADS_DIR" ]]; then
        log "ERROR: Downloads directory not found: $DOWNLOADS_DIR"
        exit 1
    fi
    
    if [[ ! -d "$HOME_DIR" ]]; then
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
        [[ -n "$file" ]] && all_files+=("$file")
    done < <(find_media_files "$DOWNLOADS_DIR")
    
    # Find files in home directory (only direct files, not subdirectories)
    log "Scanning home directory (root level only)..."
    while IFS= read -r file; do
        [[ -n "$file" ]] && all_files+=("$file")
    done < <(find_media_files "$HOME_DIR")
    
    # Create archive if files found
    if [[ ${#all_files[@]} -gt 0 ]]; then
        create_media_archive "${all_files[@]}"
        log "Media organization completed successfully."
    else
        log "No media files found to organize."
    fi
}

# Run main function
main "$@"