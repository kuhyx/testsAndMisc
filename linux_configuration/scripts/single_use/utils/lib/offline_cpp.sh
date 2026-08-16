#!/bin/bash
# C++ documentation download and indexing.
#
# Sourced by setup_offline_docs.sh; split out to keep it under the 250-line
# cap. Sourced rather than run, so it inherits the caller's strict mode
# and the variables defined above the source line.

#==============================================================================
# C/C++ Documentation (cppreference)
# Uses cppman tool which caches pages from cppreference.com
# Fallback: AUR cppreference package or direct download
#==============================================================================
download_cpp_docs() {
  print_header "C/C++ Documentation (cppreference)"
  local dest="$DOCS_DIR/c_cpp"

  if [ -f "$dest/en/index.html" ] || [ -d "$dest/reference" ] || [ -L "$dest/system" ]; then
    print_status "C/C++ docs already present"
    return 0
  fi

  mkdir -p "$dest"

  # Method 1: Use cppman if available (best - fetches and caches on demand)
  if command -v cppman &> /dev/null; then
    print_status "Found cppman, caching common C++ references..."
    cppman -s cppreference.com 2> /dev/null
    cppman -c 2> /dev/null # Cache all pages
    print_success "cppman configured - use 'cppman <term>' for lookups"
    print_status "Cppman cache at: ~/.cache/cppman/"
    ln -sf ~/.cache/cppman "$dest/cppman_cache" 2> /dev/null
    build_cpp_index
    return 0
  fi

  # Method 2: Check if system package already installed
  if [ -d /usr/share/doc/cppreference/en ]; then
    print_status "Found system cppreference package"
    ln -sf /usr/share/doc/cppreference "$dest/system"
    print_success "C/C++ documentation linked from system package"
    build_cpp_index
    return 0
  fi

  # Method 3: Try AUR package (Arch Linux)
  if command -v yay &> /dev/null; then
    print_status "Installing cppreference from AUR..."
    if yay -S --noconfirm cppreference 2> /dev/null; then
      # Link to installed docs (the package uses /en not /html)
      if [ -d /usr/share/doc/cppreference/en ]; then
        ln -sf /usr/share/doc/cppreference "$dest/system"
        print_success "C/C++ documentation linked from system package"
        build_cpp_index
        return 0
      fi
    fi
  fi

  # Method 4: Direct download (try multiple mirrors)
  print_status "Downloading cppreference offline archive..."
  local archive="/tmp/cppreference.tar.xz"
  local urls=(
    "https://upload.cppreference.com/mwiki/images/1/16/html_book_20241110.tar.xz"
    "https://github.com/nicovank/cppreference-doc/releases/latest/download/html_book.tar.xz"
  )

  for url in "${urls[@]}"; do
    print_status "Trying: $url"
    if curl -fL -o "$archive" "$url" 2> /dev/null; then
      print_status "Extracting (this may take a while)..."
      if tar -xJf "$archive" -C "$dest" 2> /dev/null; then
        rm -f "$archive"
        print_success "C/C++ documentation installed to $dest"
        build_cpp_index
        return 0
      fi
    fi
  done

  print_error "Failed to download cppreference"
  print_status "Manual install: yay -S cppreference  OR  yay -S cppman"
  return 1
}

build_cpp_index() {
  print_status "Building C/C++ documentation index..."
  local dest="$DOCS_DIR/c_cpp"
  local index="$INDEX_DIR/cpp_index.txt"

  # Resolve symlink if present
  local search_dir="$dest"
  [ -L "$dest/system" ] && search_dir="$dest/system"

  {
    # Find all HTML files and extract identifiers
    # Format: term|filepath (using | as separator to handle spaces)
    find "$search_dir" -name "*.html" -type f 2> /dev/null | while read -r file; do
      # Extract meaningful term from path (e.g., /en/cpp/container/vector.html -> vector)
      local term
      term=$(basename "$file" .html)
      # Skip index files and overly generic names
      [[ $term == "index" ]] && continue
      echo "${term}|${file}"
    done

    # Also index by path components for better discoverability
    # e.g., cpp/container/vector -> vector
    find "$search_dir/en" -name "*.html" -type f 2> /dev/null | while read -r file; do
      # Extract path relative to en/ and create searchable term
      local relpath
      relpath=$(echo "$file" | sed "s|$search_dir/en/||" | sed 's|\.html$||')
      # Get the last component as primary term
      local term
      term=$(basename "$relpath")
      [[ $term == "index" ]] && continue
      # Also add the full path as a searchable term (cpp/vector, c/stdlib/malloc)
      echo "${relpath}|${file}"
    done
  } | sort -u > "$index"

  print_success "C/C++ index created with $(wc -l < "$index") entries"
}
