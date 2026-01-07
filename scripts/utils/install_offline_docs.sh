#!/usr/bin/env bash
# Install Zeal - Offline Documentation Browser
# Downloads official documentation for: C, C++, JavaScript, TypeScript, Python
#
# Zeal is a free, open source (GPL) offline documentation browser
# Similar to Dash for macOS, uses compatible docsets

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

success() { echo -e "${GREEN}✓ $1${NC}"; }
warn() { echo -e "${YELLOW}⚠ $1${NC}"; }
error() { echo -e "${RED}✗ $1${NC}"; }
info() { echo -e "${BLUE}ℹ $1${NC}"; }

echo "=============================================="
echo " Offline Documentation Installer"
echo " Languages: C, C++, JavaScript, TypeScript, Python"
echo "=============================================="
echo ""

# Detect package manager and install Zeal
install_zeal() {
  if command -v zeal &> /dev/null; then
    success "Zeal is already installed"
    return 0
  fi

  echo "Installing Zeal offline documentation browser..."

  if command -v pacman &> /dev/null; then
    # Arch Linux
    sudo pacman -S --noconfirm zeal
  elif command -v apt &> /dev/null; then
    # Debian/Ubuntu
    sudo apt update
    sudo apt install -y zeal
  elif command -v dnf &> /dev/null; then
    # Fedora
    sudo dnf install -y zeal
  elif command -v zypper &> /dev/null; then
    # openSUSE
    sudo zypper install -y zeal
  elif command -v flatpak &> /dev/null; then
    # Flatpak fallback
    flatpak install -y flathub org.zealdocs.Zeal
  else
    error "Could not detect package manager. Please install Zeal manually:"
    echo "  https://zealdocs.org/download.html"
    return 1
  fi

  success "Zeal installed successfully"
}

# Get Zeal docsets directory
get_docsets_dir() {
  local docsets_dir

  # Check if using Flatpak
  if command -v flatpak &> /dev/null && flatpak list | grep -q "org.zealdocs.Zeal"; then
    docsets_dir="$HOME/.var/app/org.zealdocs.Zeal/data/Zeal/Zeal/docsets"
  else
    # Standard installation
    docsets_dir="$HOME/.local/share/Zeal/Zeal/docsets"
  fi

  mkdir -p "$docsets_dir"
  echo "$docsets_dir"
}

# Download a docset from Zeal feeds
download_docset() {
  local name="$1"
  local docsets_dir="$2"

  # Check if already installed
  if [ -d "$docsets_dir/${name}.docset" ]; then
    warn "$name docset already installed"
    return 0
  fi

  info "Downloading $name documentation..."

  # Use Zeal's built-in feed system via CLI or direct download
  # Zeal stores docsets in .docset directories

  # Try to get from dash-user-contributions or official feeds
  local download_url=""

  case "$name" in
    "C")
      download_url="http://kapeli.com/feeds/C.tgz"
      ;;
    "C++")
      download_url="http://kapeli.com/feeds/C%2B%2B.tgz"
      ;;
    "JavaScript")
      download_url="http://kapeli.com/feeds/JavaScript.tgz"
      ;;
    "TypeScript")
      download_url="http://kapeli.com/feeds/TypeScript.tgz"
      ;;
    "Python_3")
      download_url="http://kapeli.com/feeds/Python_3.tgz"
      ;;
    "Python_2")
      download_url="http://kapeli.com/feeds/Python_2.tgz"
      ;;
    "Bash")
      download_url="http://kapeli.com/feeds/Bash.tgz"
      ;;
    "HTML")
      download_url="http://kapeli.com/feeds/HTML.tgz"
      ;;
    "CSS")
      download_url="http://kapeli.com/feeds/CSS.tgz"
      ;;
    "NodeJS")
      download_url="http://kapeli.com/feeds/NodeJS.tgz"
      ;;
    "React")
      download_url="http://kapeli.com/feeds/React.tgz"
      ;;
    *)
      warn "Unknown docset: $name"
      return 1
      ;;
  esac

  # Download and extract
  local temp_file
  temp_file=$(mktemp)

  echo "  URL: $download_url"
  if curl -fL --progress-bar "$download_url" -o "$temp_file"; then
    echo "  Extracting to $docsets_dir..."
    tar -xzf "$temp_file" -C "$docsets_dir"
    rm -f "$temp_file"
    success "$name documentation downloaded"
  else
    rm -f "$temp_file"
    warn "Failed to download $name - you can install it from Zeal's UI"
    return 1
  fi
}

# Main installation
main() {
  # Step 1: Install Zeal
  echo ""
  echo "=== Step 1: Installing Zeal ==="
  install_zeal || exit 1

  # Step 2: Get docsets directory
  echo ""
  echo "=== Step 2: Preparing docsets directory ==="
  local docsets_dir
  docsets_dir=$(get_docsets_dir)
  success "Docsets directory: $docsets_dir"

  # Step 3: Download requested docsets
  echo ""
  echo "=== Step 3: Downloading Documentation ==="
  echo ""

  # Core requested languages
  local docsets=("C" "C++" "JavaScript" "TypeScript" "Python_3")

  # Optional extras (comment out if not needed)
  local extras=("Bash" "HTML" "CSS" "NodeJS")

  # Download core docsets
  for docset in "${docsets[@]}"; do
    download_docset "$docset" "$docsets_dir"
  done

  # Ask about extras
  echo ""
  read -r -p "Install additional docsets (Bash, HTML, CSS, NodeJS)? [Y/n] " response
  if [[ ! $response =~ ^[Nn]$ ]]; then
    for docset in "${extras[@]}"; do
      download_docset "$docset" "$docsets_dir"
    done
  fi

  # Summary
  echo ""
  echo "=============================================="
  echo " Installation Complete!"
  echo "=============================================="
  echo ""
  echo "Installed documentation:"
  for f in "$docsets_dir"/*.docset; do
    if [[ -d $f ]]; then
      echo "  ✓ $(basename "$f" .docset)"
    fi
  done
  echo ""
  echo "Usage:"
  echo "  Launch Zeal from your application menu, or run: zeal"
  echo ""
  echo "To download additional docsets:"
  echo "  1. Open Zeal"
  echo "  2. Go to Tools → Docsets"
  echo "  3. Click 'Available' tab and download what you need"
  echo ""
  echo "Keyboard shortcut tip:"
  echo "  Set a global hotkey in Zeal → Preferences → Global Shortcuts"
  echo "  (e.g., Alt+Space for quick documentation lookup)"
  echo ""
  echo "=============================================="

  # Offer to launch Zeal
  read -r -p "Launch Zeal now? [y/N] " response
  if [[ $response =~ ^[Yy]$ ]]; then
    nohup zeal &> /dev/null &
    success "Zeal launched"
  fi
}

main "$@"
