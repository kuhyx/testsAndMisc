#!/bin/bash
# JavaScript documentation download and indexing.
#
# Sourced by setup_offline_docs.sh; split out to keep offline_cpp.sh under the
# 250-line cap. Sourced rather than run, so it inherits the caller's
# strict mode and the variables defined above the source line.

#==============================================================================
# JavaScript/MDN Documentation
# Clone the actual MDN content repository for full documentation
# https://github.com/mdn/content
#==============================================================================
download_js_docs() {
  print_header "JavaScript/MDN Documentation"
  local dest="$DOCS_DIR/javascript"
  local mdn_repo="$DOCS_DIR/mdn-content"

  # Check if already cloned
  if [ -d "$mdn_repo/files/en-us/web/javascript" ]; then
    print_status "MDN content already present"
    build_js_index
    return 0
  fi

  print_status "Cloning MDN content repository (sparse checkout for web docs)..."
  print_status "This may take a few minutes on first run..."

  mkdir -p "$mdn_repo"
  cd "$mdn_repo" || exit 1

  # Initialize sparse checkout to only get what we need
  if [ ! -d ".git" ]; then
    git init
    git remote add origin https://github.com/mdn/content.git
    git config core.sparseCheckout true

    # Only checkout web-related documentation (JS, HTML, CSS, Web APIs)
    cat > .git/info/sparse-checkout << 'SPARSE'
/files/en-us/web/javascript/
/files/en-us/web/api/
/files/en-us/web/html/
/files/en-us/web/css/
/files/en-us/glossary/
SPARSE

    print_status "Fetching MDN content (JavaScript, HTML, CSS, Web APIs)..."
    git fetch --depth 1 origin main
    git checkout main
  else
    print_status "Updating MDN content..."
    git pull --depth 1 origin main 2> /dev/null || true
  fi

  cd - > /dev/null || exit 1

  # Create symlink for easier access
  mkdir -p "$dest"
  ln -sf "$mdn_repo/files/en-us/web/javascript" "$dest/javascript"
  ln -sf "$mdn_repo/files/en-us/web/api" "$dest/web-api"
  ln -sf "$mdn_repo/files/en-us/web/html" "$dest/html"
  ln -sf "$mdn_repo/files/en-us/web/css" "$dest/css"
  ln -sf "$mdn_repo/files/en-us/glossary" "$dest/glossary"

  build_js_index
  print_success "MDN offline documentation ready"

  local doc_count
  doc_count=$(find "$mdn_repo/files" -name "index.md" 2> /dev/null | wc -l)
  print_status "Downloaded $doc_count documentation pages"
}

build_js_index() {
  print_status "Building MDN documentation index..."
  local mdn_repo="$DOCS_DIR/mdn-content"
  local index="$INDEX_DIR/js_index.txt"

  if [ ! -d "$mdn_repo/files" ]; then
    print_error "MDN content not found"
    return 1
  fi

  # Build comprehensive index from MDN markdown files
  {
    # Index JavaScript reference
    find "$mdn_repo/files/en-us/web/javascript/reference" -name "index.md" 2> /dev/null | while read -r file; do
      local dir
      dir=$(dirname "$file")
      local term
      term=$(basename "$dir")
      # Extract title from frontmatter if available
      local title
      title=$(grep -m1 "^title:" "$file" 2> /dev/null | sed 's/^title:\s*//' | tr -d '"')
      echo "${term}|${file}|${title:-$term}"
    done

    # Index Web APIs
    find "$mdn_repo/files/en-us/web/api" -name "index.md" 2> /dev/null | while read -r file; do
      local dir
      dir=$(dirname "$file")
      local term
      term=$(basename "$dir")
      local title
      title=$(grep -m1 "^title:" "$file" 2> /dev/null | sed 's/^title:\s*//' | tr -d '"')
      echo "${term}|${file}|${title:-$term}"
    done

    # Index HTML elements
    find "$mdn_repo/files/en-us/web/html/element" -name "index.md" 2> /dev/null | while read -r file; do
      local dir
      dir=$(dirname "$file")
      local term
      term=$(basename "$dir")
      echo "${term}|${file}|HTML <${term}> element"
    done

    # Index CSS properties
    find "$mdn_repo/files/en-us/web/css" -maxdepth 2 -name "index.md" 2> /dev/null | while read -r file; do
      local dir
      dir=$(dirname "$file")
      local term
      term=$(basename "$dir")
      local title
      title=$(grep -m1 "^title:" "$file" 2> /dev/null | sed 's/^title:\s*//' | tr -d '"')
      echo "${term}|${file}|${title:-$term}"
    done

    # Index Glossary
    find "$mdn_repo/files/en-us/glossary" -name "index.md" 2> /dev/null | while read -r file; do
      local dir
      dir=$(dirname "$file")
      local term
      term=$(basename "$dir")
      local title
      title=$(grep -m1 "^title:" "$file" 2> /dev/null | sed 's/^title:\s*//' | tr -d '"')
      echo "${term}|${file}|${title:-$term}"
    done
  } | sort -t'|' -k1,1 -u > "$index"

  local count
  count=$(wc -l < "$index")
  print_success "MDN index created with $count entries"
}
