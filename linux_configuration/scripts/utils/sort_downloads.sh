#!/bin/bash

# Function to sort files in a given directory
sort_files() {
  local dir=$1
  cd "$dir" || return 1

  local old_nullglob
  old_nullglob=$(shopt -p nullglob || true)
  shopt -s nullglob

  # Create directories if they do not exist
  mkdir -p images videos documents

  # Move video files to the videos folder
  mv -- ./*.webm ./*.mp4 ./*.mkv ./*.avi ./*.mov ./*.flv videos/ 2> /dev/null

  # Move image files to the images folder
  mv -- ./*.png ./*.jpg ./*.jpeg ./*.gif ./*.webp ./*.bmp images/ 2> /dev/null

  # Move document files to the documents folder
  mv -- ./*.pdf ./*.doc ./*.docx ./*.txt ./*.odt documents/ 2> /dev/null

  if [[ -n $old_nullglob ]]; then
    eval "$old_nullglob"
  else
    shopt -u nullglob
  fi
}

# Sort files in the Downloads folder
sort_files ~/Downloads

# Sort files in the home folder
sort_files ~
