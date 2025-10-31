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
> "$output_file"

# Process file using a pipeline of specialized tools
# 1. tr - remove non-alphabetic chars except newlines
# 2. tr - convert to uppercase 
# 3. grep - filter by length (5-8 characters)
# 4. sort - sort the words alphabetically
# 5. uniq - remove duplicates
tr -cd 'a-zA-Z\n' < "$1" | tr '[:lower:]' '[:upper:]' | grep -x '.\{5,8\}' | sort | uniq > "$output_file"

echo "Processing complete. Results saved to '$output_file'"
