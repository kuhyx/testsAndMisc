#!/bin/bash

# Default values
TARGET_EXT="mp4"
TARGET_SIZE=10M

# Parse arguments
if [ -n "$1" ]; then
  INPUT_PATH="$1"
else
  INPUT_PATH="."
fi

if [ -n "$2" ]; then
  TARGET_EXT="$2"
fi

if [ -n "$3" ]; then
  TARGET_SIZE="$3"
fi

# Create output directory
OUTPUT_DIR="converted"
mkdir -p "$OUTPUT_DIR"

# Function to convert video
convert_video() {
  local input_file="$1"
  local output_file="$OUTPUT_DIR/${input_file%.*}.$TARGET_EXT"
  
  # Get video duration in seconds
  DURATION=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$input_file")
  echo "Duration: $DURATION seconds"
  
  # Convert target size to bytes
  TARGET_SIZE_BYTES=$(numfmt --from=iec "$TARGET_SIZE")
    
  # Calculate target bitrate in kilobits per second
  TARGET_BITRATE=$(echo "($TARGET_SIZE_BYTES * 8) / $DURATION / 2000" | bc) # Reduce by 10% to ensure size is below target
  
  # Convert video
  ffmpeg -i "$input_file" -b:v "${TARGET_BITRATE}k" -c:a copy "$output_file"
  
  # Get original and converted video sizes
  ORIGINAL_SIZE=$(stat -c%s "$input_file")
  CONVERTED_SIZE=$(stat -c%s "$output_file")
  
  # Print out details
  echo "Original size: $(numfmt --to=iec $ORIGINAL_SIZE)"
  echo "Video length: $DURATION seconds"
  echo "Target size: $TARGET_SIZE"
  echo "Converted size: $(numfmt --to=iec $CONVERTED_SIZE)"
  echo "Target bitrate: ${TARGET_BITRATE}kbps"
}

# Export function for find command
export -f convert_video
export TARGET_EXT
export TARGET_SIZE
export OUTPUT_DIR

# Find and convert videos
if [ -d "$INPUT_PATH" ]; then
  find "$INPUT_PATH" -type f -name "*.mp4" -o -name "*.mkv" -o -name "*.avi" -o -name "*.webm" -exec bash -c 'convert_video "$0"' {} \;
else
  convert_video "$INPUT_PATH"
fi
