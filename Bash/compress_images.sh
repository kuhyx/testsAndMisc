#!/bin/bash

# Directory containing the images
directory="./images"

# Compression level (default to 0 if not provided)
compression_level=${1:-0}

# Create output directory, overwrite if it already exists
output_directory="${directory}/webp"
rm -rf "$output_directory"
mkdir -p "$output_directory"

# Iterate through each file in the directory
for file in "$directory"/*.{jpg,jpeg,png,bmp,tiff}; do
  # Skip if no matching files are found
  [ -e "$file" ] || continue

  # Extract the filename without extension
  filename=$(basename "$file")
  filename_no_ext="${filename%.*}"

  # Convert the file to WebP with specified compression level
  cwebp -q "$compression_level" "$file" -o "$output_directory/${filename_no_ext}.webp"

  echo "Converted: $file -> $output_directory/${filename_no_ext}.webp"
done

echo "All images have been converted to WebP with compression level $compression_level."
