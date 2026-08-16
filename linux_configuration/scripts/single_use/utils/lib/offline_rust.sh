#!/bin/bash
# Rust documentation download and indexing.
#
# Sourced by setup_offline_docs.sh; split out to keep offline_js.sh under the
# 250-line cap. Sourced rather than run, so it inherits the caller's
# strict mode and the variables defined above the source line.

#==============================================================================
# Rust Documentation (via rustup)
#==============================================================================
download_rust_docs() {
  print_header "Rust Documentation"
  local dest="$DOCS_DIR/rust"

  if command -v rustup &> /dev/null; then
    print_status "Rust docs available via 'rustup doc'"

    # Get the rust doc path
    local rust_doc_path
    rust_doc_path=$(rustup doc --path 2> /dev/null | head -1 | xargs dirname 2> /dev/null)

    if [ -n "$rust_doc_path" ] && [ -d "$rust_doc_path" ]; then
      ln -sf "$rust_doc_path" "$dest/std"
      print_success "Linked Rust std docs from $rust_doc_path"
      build_rust_index
    fi
  else
    print_status "Rust not installed. Install with: curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"
  fi
}
