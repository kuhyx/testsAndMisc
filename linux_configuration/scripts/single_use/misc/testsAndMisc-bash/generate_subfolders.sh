#!/bin/bash

# Function to generate random number between two values
random_number() {
  echo $((RANDOM % ($2 - $1 + 1) + $1))
}

# Function to generate random string with non-computer-friendly characters
random_string() {
  local length="$1"
  tr -dc 'a-zA-Z0-9!@#$%^&*()_+{}|:<>?~' < /dev/urandom | head -c "$length"
}

# Function to calculate total number of folders to be created
calculate_total_folders() {
  local depth="$1"
  local total=0
  if [ "$depth" -le 10 ]; then
    local num_subfolders
    num_subfolders=$(random_number 1 50)
    total=$((num_subfolders + total))
    for ((i = 1; i <= num_subfolders; i++)); do
      total=$((total + $(calculate_total_folders $((depth + 1)))))
    done
  fi
  echo "$total"
}

# Function to create folders and files recursively
create_structure() {
  local current_depth="$1"
  local parent_dir="$2"
  local start_time="$3"

  if [ "$current_depth" -le 10 ]; then
    local num_subfolders
    num_subfolders=$(random_number 1 50)
    echo "Creating $num_subfolders subfolders at depth $current_depth"
    for ((i = 1; i <= num_subfolders; i++)); do
      local subfolder
      subfolder="$parent_dir/$(random_string 255)"
      mkdir -p "$subfolder"
      ((generated_folders++))

      # Display progress
      local elapsed_time
      elapsed_time=$(($(date +%s) - start_time))
      local estimated_total_time
      estimated_total_time=$((elapsed_time * total_folders / generated_folders))
      local remaining_time
      remaining_time=$((estimated_total_time - elapsed_time))
      echo "Generated: $generated_folders/$total_folders folders. Estimated time left: $remaining_time seconds."

      # Create random number of empty files
      local num_files
      num_files=$(random_number 10 100)
      echo "Creating $num_files files"
      for ((j = 1; j <= num_files; j++)); do
        touch "$subfolder/$(random_string 255)"
      done

      # Recursively create subfolders
      create_structure $((current_depth + 1)) "$subfolder" "$start_time"
    done
  fi
}

# Main folder
main_folder="/home/k.rudnicki@aiclearing.com/testsAndMisc/Bash/main_folder"
mkdir -p "$main_folder"

# Calculate total folders to be created (best-effort). If calculation is expensive, you can uncomment.
# total_folders=$(calculate_total_folders 1)
# Fallback when not precomputed: estimate grows as we generate
total_folders=${total_folders:-0}
generated_folders=0

echo "Total folders to be generated: ${total_folders:-unknown}"

# Start creating structure from the main folder
start_time=$(date +%s)
create_structure 1 "$main_folder" "$start_time"
