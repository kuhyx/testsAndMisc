#!/bin/bash
#==============================================================================
# Offline Documentation Setup
# Downloads and indexes official documentation for multiple programming languages
#
# Usage: ./setup_offline_docs.sh [--all | --python | --c | --js | --rust | --go]
#
# Documentation is stored in: ~/.local/share/offline-docs/
#==============================================================================

set -e

# Configuration
DOCS_DIR="${OFFLINE_DOCS_DIR:-$HOME/.local/share/offline-docs}"
INDEX_DIR="$DOCS_DIR/.index"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_header() {
    echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  $1${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
}

print_status() {
    echo -e "${YELLOW}→${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Create directory structure
setup_dirs() {
    mkdir -p "$DOCS_DIR"/{python,c_cpp,javascript,typescript,rust,go,ruby,java,shell}
    mkdir -p "$INDEX_DIR"
}

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
    
    if curl -L -o "$archive" "$url" 2>/dev/null; then
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
        find "$dest/library" -name "*.html" -exec basename {} .html \; 2>/dev/null | while read -r mod; do
            echo "$mod $dest/library/$mod.html"
        done
        
        # Index built-in functions from functions.html
        if [ -f "$dest/library/functions.html" ]; then
            grep -oP '(?<=id=")[^"]+' "$dest/library/functions.html" 2>/dev/null | while read -r func; do
                echo "$func $dest/library/functions.html#$func"
            done
        fi
        
        # Index from general index
        if [ -f "$dest/genindex.html" ]; then
            grep -oP 'href="([^"]+)"[^>]*>([^<]+)' "$dest/genindex.html" 2>/dev/null | \
                sed -E 's/href="([^"]+)"[^>]*>([^<]+)/\2 \1/' | \
                head -5000
        fi
    } | sort -u > "$index"
    
    print_success "Python index created with $(wc -l < "$index") entries"
}

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
    if command -v cppman &>/dev/null; then
        print_status "Found cppman, caching common C++ references..."
        cppman -s cppreference.com 2>/dev/null
        cppman -c 2>/dev/null  # Cache all pages
        print_success "cppman configured - use 'cppman <term>' for lookups"
        print_status "Cppman cache at: ~/.cache/cppman/"
        ln -sf ~/.cache/cppman "$dest/cppman_cache" 2>/dev/null
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
    if command -v yay &>/dev/null; then
        print_status "Installing cppreference from AUR..."
        if yay -S --noconfirm cppreference 2>/dev/null; then
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
        if curl -fL -o "$archive" "$url" 2>/dev/null; then
            print_status "Extracting (this may take a while)..."
            if tar -xJf "$archive" -C "$dest" 2>/dev/null; then
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
        find "$search_dir" -name "*.html" -type f 2>/dev/null | while read -r file; do
            # Extract meaningful term from path (e.g., /en/cpp/container/vector.html -> vector)
            local term
            term=$(basename "$file" .html)
            # Skip index files and overly generic names
            [[ "$term" == "index" ]] && continue
            echo "${term}|${file}"
        done
        
        # Also index by path components for better discoverability
        # e.g., cpp/container/vector -> vector
        find "$search_dir/en" -name "*.html" -type f 2>/dev/null | while read -r file; do
            # Extract path relative to en/ and create searchable term
            local relpath
            relpath=$(echo "$file" | sed "s|$search_dir/en/||" | sed 's|\.html$||')
            # Get the last component as primary term
            local term
            term=$(basename "$relpath")
            [[ "$term" == "index" ]] && continue
            # Also add the full path as a searchable term (cpp/vector, c/stdlib/malloc)
            echo "${relpath}|${file}"
        done
    } | sort -u > "$index"
    
    print_success "C/C++ index created with $(wc -l < "$index") entries"
}

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
        git pull --depth 1 origin main 2>/dev/null || true
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
    doc_count=$(find "$mdn_repo/files" -name "index.md" 2>/dev/null | wc -l)
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
        find "$mdn_repo/files/en-us/web/javascript/reference" -name "index.md" 2>/dev/null | while read -r file; do
            local dir
            dir=$(dirname "$file")
            local term
            term=$(basename "$dir")
            # Extract title from frontmatter if available
            local title
            title=$(grep -m1 "^title:" "$file" 2>/dev/null | sed 's/^title:\s*//' | tr -d '"')
            echo "${term}|${file}|${title:-$term}"
        done
        
        # Index Web APIs
        find "$mdn_repo/files/en-us/web/api" -name "index.md" 2>/dev/null | while read -r file; do
            local dir
            dir=$(dirname "$file")
            local term
            term=$(basename "$dir")
            local title
            title=$(grep -m1 "^title:" "$file" 2>/dev/null | sed 's/^title:\s*//' | tr -d '"')
            echo "${term}|${file}|${title:-$term}"
        done
        
        # Index HTML elements
        find "$mdn_repo/files/en-us/web/html/element" -name "index.md" 2>/dev/null | while read -r file; do
            local dir
            dir=$(dirname "$file")
            local term
            term=$(basename "$dir")
            echo "${term}|${file}|HTML <${term}> element"
        done
        
        # Index CSS properties
        find "$mdn_repo/files/en-us/web/css" -maxdepth 2 -name "index.md" 2>/dev/null | while read -r file; do
            local dir
            dir=$(dirname "$file")
            local term
            term=$(basename "$dir")
            local title
            title=$(grep -m1 "^title:" "$file" 2>/dev/null | sed 's/^title:\s*//' | tr -d '"')
            echo "${term}|${file}|${title:-$term}"
        done
        
        # Index Glossary
        find "$mdn_repo/files/en-us/glossary" -name "index.md" 2>/dev/null | while read -r file; do
            local dir
            dir=$(dirname "$file")
            local term
            term=$(basename "$dir")
            local title
            title=$(grep -m1 "^title:" "$file" 2>/dev/null | sed 's/^title:\s*//' | tr -d '"')
            echo "${term}|${file}|${title:-$term}"
        done
    } | sort -t'|' -k1,1 -u > "$index"
    
    local count
    count=$(wc -l < "$index")
    print_success "MDN index created with $count entries"
}

#==============================================================================
# Rust Documentation (via rustup)
#==============================================================================
download_rust_docs() {
    print_header "Rust Documentation"
    local dest="$DOCS_DIR/rust"
    
    if command -v rustup &>/dev/null; then
        print_status "Rust docs available via 'rustup doc'"
        
        # Get the rust doc path
        local rust_doc_path
        rust_doc_path=$(rustup doc --path 2>/dev/null | head -1 | xargs dirname 2>/dev/null)
        
        if [ -n "$rust_doc_path" ] && [ -d "$rust_doc_path" ]; then
            ln -sf "$rust_doc_path" "$dest/std"
            print_success "Linked Rust std docs from $rust_doc_path"
            build_rust_index
        fi
    else
        print_status "Rust not installed. Install with: curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"
    fi
}

build_rust_index() {
    print_status "Building Rust documentation index..."
    local index="$INDEX_DIR/rust_index.txt"
    
    if command -v rustup &>/dev/null; then
        local rust_doc_path
        rust_doc_path=$(rustup doc --path 2>/dev/null | head -1 | xargs dirname 2>/dev/null)
        
        if [ -d "$rust_doc_path/std" ]; then
            find "$rust_doc_path/std" -name "*.html" 2>/dev/null | head -2000 | while read -r file; do
                basename "$file" .html
            done | sort -u > "$index"
        fi
    fi
    
    print_success "Rust index created"
}

#==============================================================================
# Go Documentation
#==============================================================================
download_go_docs() {
    print_header "Go Documentation"
    local dest="$DOCS_DIR/go"
    
    if command -v go &>/dev/null; then
        print_status "Go docs available via 'go doc'"
        
        # Create a reference of standard library packages
        mkdir -p "$dest"
        go list std 2>/dev/null > "$dest/stdlib_packages.txt"
        
        print_success "Go stdlib package list created"
        build_go_index
    else
        print_status "Go not installed"
    fi
}

build_go_index() {
    print_status "Building Go documentation index..."
    local dest="$DOCS_DIR/go"
    local index="$INDEX_DIR/go_index.txt"
    
    if [ -f "$dest/stdlib_packages.txt" ]; then
        cp "$dest/stdlib_packages.txt" "$index"
    fi
    
    print_success "Go index created"
}

#==============================================================================
# Shell/Bash Documentation (man pages + built-in help)
#==============================================================================
download_shell_docs() {
    print_header "Shell/Bash Documentation"
    local dest="$DOCS_DIR/shell"
    mkdir -p "$dest"
    
    print_status "Extracting bash built-in help..."
    
    # Extract help for all bash builtins
    {
        echo "# Bash Built-in Commands Reference"
        echo "# Generated from 'help' command"
        echo ""
        
        # Get list of builtins
        compgen -b 2>/dev/null | while read -r builtin; do
            echo "=== $builtin ==="
            help "$builtin" 2>/dev/null || echo "No help available"
            echo ""
        done
    } > "$dest/bash_builtins.txt"
    
    # Create quick reference for common commands
    cat > "$dest/common_commands.txt" << 'SHELLREF'
# Common Shell Commands Quick Reference

## File Operations
ls      - List directory contents
cd      - Change directory
pwd     - Print working directory
cp      - Copy files
mv      - Move/rename files
rm      - Remove files
mkdir   - Create directory
rmdir   - Remove empty directory
touch   - Create empty file / update timestamp
cat     - Concatenate and display files
head    - Display first lines
tail    - Display last lines
less    - Page through file
find    - Search for files
locate  - Find files by name (uses database)

## Text Processing
grep    - Search text patterns
sed     - Stream editor
awk     - Pattern scanning and processing
cut     - Remove sections from lines
sort    - Sort lines
uniq    - Report or omit repeated lines
wc      - Word, line, character count
tr      - Translate characters
diff    - Compare files

## Process Management
ps      - Report process status
top     - Display processes
kill    - Send signal to process
pkill   - Kill processes by name
bg      - Background a process
fg      - Foreground a process
jobs    - List background jobs
nohup   - Run immune to hangups

## Networking
curl    - Transfer data from URL
wget    - Download files
ssh     - Secure shell
scp     - Secure copy
rsync   - Remote sync
ping    - Test connectivity
netstat - Network statistics
ss      - Socket statistics

## Archives
tar     - Tape archive
gzip    - Compress files
gunzip  - Decompress files
zip     - Package and compress
unzip   - Extract zip archives

## Permissions
chmod   - Change file permissions
chown   - Change file owner
chgrp   - Change file group

## Disk
df      - Disk free space
du      - Disk usage
mount   - Mount filesystem
umount  - Unmount filesystem

## System
uname   - System information
hostname - Show/set hostname
uptime  - System uptime
free    - Memory usage
date    - Display/set date
cal     - Display calendar

## Bash Builtins
echo    - Display text
printf  - Formatted output
read    - Read input
export  - Set environment variable
source  - Execute script in current shell
alias   - Create command alias
type    - Display command type
which   - Locate command
declare - Declare variables
local   - Local variable
set     - Set shell options
shopt   - Shell options
trap    - Trap signals
eval    - Evaluate arguments
exec    - Execute command
SHELLREF

    print_success "Shell documentation created"
    build_shell_index
}

build_shell_index() {
    print_status "Building Shell documentation index..."
    local dest="$DOCS_DIR/shell"
    local index="$INDEX_DIR/shell_index.txt"
    
    {
        # Bash builtins
        compgen -b 2>/dev/null | while read -r cmd; do
            echo "$cmd $dest/bash_builtins.txt"
        done
        
        # Common commands from man pages
        for cmd in ls cd cp mv rm mkdir cat grep sed awk find sort curl wget tar chmod; do
            man_path=$(man -w "$cmd" 2>/dev/null)
            [ -n "$man_path" ] && echo "$cmd $man_path"
        done
    } | sort -u > "$index"
    
    print_success "Shell index created"
}

#==============================================================================
# Zeal Docsets (cross-platform dash alternative)
#==============================================================================
setup_zeal_docsets() {
    print_header "Zeal Docsets (Optional)"
    
    if ! command -v zeal &>/dev/null; then
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
        if [ -d "$dir" ] && [ "$(ls -A "$dir" 2>/dev/null)" ]; then
            size=$(du -sh "$dir" 2>/dev/null | cut -f1)
            print_success "$lang: installed ($size)"
        else
            print_error "$lang: not installed"
        fi
    done
    
    echo ""
    echo "Index files:"
    ls -la "$INDEX_DIR"/*.txt 2>/dev/null || echo "No indexes built yet"
}

main() {
    setup_dirs
    
    if [ $# -eq 0 ]; then
        usage
        exit 0
    fi
    
    while [ $# -gt 0 ]; do
        case "$1" in
            --all)
                download_python_docs
                download_cpp_docs
                download_js_docs
                download_rust_docs
                download_go_docs
                download_shell_docs
                setup_zeal_docsets
                ;;
            --python)
                download_python_docs
                ;;
            --cpp|--c|--c++)
                download_cpp_docs
                ;;
            --js|--javascript)
                download_js_docs
                ;;
            --rust)
                download_rust_docs
                ;;
            --go)
                download_go_docs
                ;;
            --shell|--bash)
                download_shell_docs
                ;;
            --zeal)
                setup_zeal_docsets
                ;;
            --status)
                show_status
                ;;
            --help|-h)
                usage
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
        shift
    done
    
    echo ""
    print_header "Setup Complete"
    echo "Documentation stored in: $DOCS_DIR"
    echo ""
    echo "Use 'lookup_docs.sh <term> [language]' to search documentation"
}

main "$@"
