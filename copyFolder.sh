#!/bin/bash

# Get the list of directories in the current script directory
directories=($(find . -maxdepth 1 -type d ! -name .))

# Check if there is exactly one directory
if [ ${#directories[@]} -ne 1 ]; then
  echo "Error: There should be exactly one folder in the current directory."
  exit 1
fi

# Get the name of the single directory
folder_name=${directories[0]}

random_string() {
    local length=$1
    tr -dc 'a-zA-Z0-9!@#$%^&*()_+{}|:<>?~' < /dev/urandom | head -c $length
}

# Number of copies to create (default 100)
num_copies=${1:-100}

# Create the specified number of copies
for ((i=1; i<=num_copies; i++)); do
    new_folder_name="$(random_string 255)"
    cp -r "$folder_name" "$new_folder_name"
    echo "Folder copied and renamed to '$new_folder_name'"
done