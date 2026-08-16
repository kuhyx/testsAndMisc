#!/bin/bash
# Python documentation download and indexing.
#
# Sourced by setup_offline_docs.sh; split out to keep it under the 250-line
# cap. Sourced rather than run, so it inherits the caller's strict mode
# and the variables defined above the source line.

#==============================================================================
# Python Documentation
# Source: https://docs.python.org/3/download.html
#==============================================================================
download_python_docs() {
  print_header "Python Documentation"
  local dest="$DOCS_DIR/python"

  # Check if already downloaded
  if [ -f "$dest/library/index.html" ]; then
    print_status "Python docs already present, checking for updates..."
  fi

  print_status "Downloading Python 3.12 documentation..."

  # Download HTML documentation (most searchable)
  local url="https://www.python.org/ftp/python/doc/3.12.8/python-3.12.8-docs-html.tar.bz2"
  local archive="/tmp/python-docs.tar.bz2"

  if curl -L -o "$archive" "$url" 2> /dev/null; then
    print_status "Extracting..."
    tar -xjf "$archive" -C "$dest" --strip-components=1
    rm -f "$archive"
    print_success "Python documentation installed to $dest"

    # Build index
    build_python_index
  else
    print_error "Failed to download Python docs"
    print_status "Alternative: Use 'python -m pydoc' for built-in docs"
  fi
}

build_python_index() {
  print_status "Building Python documentation index..."
  local dest="$DOCS_DIR/python"
  local index="$INDEX_DIR/python_index.txt"

  # Create searchable index: term -> file path
  {
    # Index library modules
    find "$dest/library" -name "*.html" -exec basename {} .html \; 2> /dev/null | while read -r mod; do
      echo "$mod $dest/library/$mod.html"
    done

    # Index built-in functions from functions.html
    if [ -f "$dest/library/functions.html" ]; then
      grep -oP '(?<=id=")[^"]+' "$dest/library/functions.html" 2> /dev/null | while read -r func; do
        echo "$func $dest/library/functions.html#$func"
      done
    fi

    # Index from general index
    if [ -f "$dest/genindex.html" ]; then
      grep -oP 'href="([^"]+)"[^>]*>([^<]+)' "$dest/genindex.html" 2> /dev/null |
        sed -E 's/href="([^"]+)"[^>]*>([^<]+)/\2 \1/' |
        head -5000
    fi
  } | sort -u > "$index"

  print_success "Python index created with $(wc -l < "$index") entries"
}
