#!/bin/bash
# Zeal docset setup, usage text and the status report.
#
# Sourced by setup_offline_docs.sh; split out to keep offline_index.sh
# under the 250-line cap. Sourced rather than run, so it inherits the
# caller's strict mode and the variables defined above the source line.

#==============================================================================
# Zeal Docsets (cross-platform dash alternative)
#==============================================================================
setup_zeal_docsets() {
  print_header "Zeal Docsets (Optional)"

  if ! command -v zeal &> /dev/null; then
    print_status "Zeal not installed."
    print_status "Install with: pacman -S zeal (or your package manager)"
    print_status "Zeal provides a GUI for offline documentation"
    return 0
  fi

  print_status "Zeal is installed. You can download docsets from within Zeal."
  print_status "Recommended docsets: Python 3, JavaScript, TypeScript, C, C++"
}

#==============================================================================
# Main
#==============================================================================
usage() {
  cat << EOF
Usage: $0 [OPTIONS]

Download and setup offline documentation for programming languages.

Options:
    --all       Download all available documentation
    --python    Download Python documentation
    --cpp, --c  Download C/C++ documentation (cppreference)
    --js        Download JavaScript documentation
    --rust      Download/link Rust documentation
    --go        Download/link Go documentation
    --shell     Generate Shell/Bash documentation
    --zeal      Setup Zeal docsets info
    --status    Show what's installed
    --help      Show this help

Documentation is stored in: $DOCS_DIR

Examples:
    $0 --all              # Download everything
    $0 --python --cpp     # Download Python and C++ docs
    $0 --status           # Check what's installed
EOF
}

show_status() {
  print_header "Offline Documentation Status"
  echo "Documentation directory: $DOCS_DIR"
  echo ""

  for lang in python c_cpp javascript rust go shell; do
    dir="$DOCS_DIR/$lang"
    if [ -d "$dir" ] && [ "$(ls -A "$dir" 2> /dev/null)" ]; then
      size=$(du -sh "$dir" 2> /dev/null | cut -f1)
      print_success "$lang: installed ($size)"
    else
      print_error "$lang: not installed"
    fi
  done

  echo ""
  echo "Index files:"
  ls -la "$INDEX_DIR"/*.txt 2> /dev/null || echo "No indexes built yet"
}
