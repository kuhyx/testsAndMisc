#!/bin/bash
# Index building and the combined docs summary.
#
# Sourced by setup_offline_docs.sh; split out to keep offline_rust.sh
# under the 250-line cap. Sourced rather than run, so it inherits the
# caller's strict mode and the variables defined above the source line.

build_rust_index() {
  print_status "Building Rust documentation index..."
  local index="$INDEX_DIR/rust_index.txt"

  if command -v rustup &> /dev/null; then
    local rust_doc_path
    rust_doc_path=$(rustup doc --path 2> /dev/null | head -1 | xargs dirname 2> /dev/null)

    if [ -d "$rust_doc_path/std" ]; then
      find "$rust_doc_path/std" -name "*.html" 2> /dev/null | head -2000 | while read -r file; do
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

  if command -v go &> /dev/null; then
    print_status "Go docs available via 'go doc'"

    # Create a reference of standard library packages
    mkdir -p "$dest"
    go list std 2> /dev/null > "$dest/stdlib_packages.txt"

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
    compgen -b 2> /dev/null | while read -r builtin; do
      echo "=== $builtin ==="
      help "$builtin" 2> /dev/null || echo "No help available"
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
    compgen -b 2> /dev/null | while read -r cmd; do
      echo "$cmd $dest/bash_builtins.txt"
    done

    # Common commands from man pages
    for cmd in ls cd cp mv rm mkdir cat grep sed awk find sort curl wget tar chmod; do
      man_path=$(man -w "$cmd" 2> /dev/null)
      [ -n "$man_path" ] && echo "$cmd $man_path"
    done
  } | sort -u > "$index"

  print_success "Shell index created"
}
