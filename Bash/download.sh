#!/bin/bash

# Check if there are any .txt files in the current directory
txt_files=(*.txt)
if [ ${#txt_files[@]} -eq 0 ]; then
    echo "No .txt files found in the current directory!"
    exit 1
fi

total_files=0
total_size=0
downloaded_files=0
downloaded_size=0

# Calculate total number of files and total size to download
for file in *.txt; do
    while IFS= read -r url; do
        if [[ -n "$url" ]]; then
            total_files=$((total_files + 1))
            size=$(wget --spider "$url" 2>&1 | grep Length | awk '{print $2}')
            total_size=$((total_size + size))
        fi
    done < "$file"
done

# Loop through each .txt file and download each URL in parallel
for file in *.txt; do
    echo "Processing $file..."
    while IFS= read -r url; do
        if [[ -n "$url" ]]; then
            {
                wget -q --show-progress "$url"
                downloaded_files=$((downloaded_files + 1))
                size=$(wget --spider "$url" 2>&1 | grep Length | awk '{print $2}')
                downloaded_size=$((downloaded_size + size))
                remaining_files=$((total_files - downloaded_files))
                remaining_size=$((total_size - downloaded_size))
                echo "Downloaded: $downloaded_files/$total_files files, $downloaded_size/$total_size bytes"
                echo "Remaining: $remaining_files files, $remaining_size bytes"
            } &
        fi
    done < "$file"
done

# Wait for all background jobs to complete
wait