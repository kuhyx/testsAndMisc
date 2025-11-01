#!/bin/bash

# Simple test script to debug file removal

set -euo pipefail

DOWNLOADS_DIR="$HOME/Downloads"

# Test function
test_file_removal() {
  local files=()

  # Find a few test files
  while IFS= read -r -d '' file; do
    files+=("$file")
  done < <(find "$DOWNLOADS_DIR" -name "*.jpg" -print0 2> /dev/null | head -z -n 2)

  echo "Found ${#files[@]} test files:"
  for file in "${files[@]}"; do
    echo "  - $file"
  done

  echo "Attempting to remove files..."
  local removed=0
  local failed=0

  for file in "${files[@]}"; do
    echo "Removing: $file"
    if rm "$file" 2> /dev/null; then
      echo "  SUCCESS"
      ((removed++))
    else
      echo "  FAILED (exit code: $?)"
      ((failed++))
    fi
  done

  echo "Results: $removed removed, $failed failed"
}

test_file_removal
