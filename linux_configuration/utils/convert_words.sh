#!/bin/bash

# Check if input and output files are provided
if [ $# -ne 2 ]; then
  echo "Usage: $0 input_file.txt output_file.txt"
  exit 1
fi

# Check if the input file exists
if [ ! -f "$1" ]; then
  echo "Error: File '$1' not found"
  exit 1
fi

# Store output file name
output_file="$2"

# Clear output file at the beginning
: > "$output_file"

# Process file: extract 5-8 char alphabetic words, uppercase, deduplicate
# grep -oE extracts words directly (replaces two tr passes), sort -u deduplicates
grep -oE '[a-zA-Z]{5,8}' < "$1" | tr '[:lower:]' '[:upper:]' | sort -u > "$output_file"

echo "Processing complete. Results saved to '$output_file'"
