#!/bin/bash

# ImageViewer Installation Script for Arch Linux
# This script installs dependencies, builds, and installs the imageviewer

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="/usr/local/bin"
DESKTOP_FILE_DIR="/usr/local/share/applications"
ICON_DIR="/usr/local/share/pixmaps"

print_step() {
    echo -e "${BLUE}==>${NC} ${1}"
}

print_success() {
    echo -e "${GREEN}✓${NC} ${1}"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} ${1}"
}

print_error() {
    echo -e "${RED}✗${NC} ${1}"
}

check_arch() {
    if [[ ! -f /etc/arch-release ]]; then
        print_error "This script is designed for Arch Linux only."
        exit 1
    fi
    print_success "Arch Linux detected"
}

check_permissions() {
    if [[ $EUID -eq 0 ]]; then
        print_warning "Running as root. This script should be run as a regular user."
        print_warning "It will prompt for sudo when needed."
    fi
}

install_dependencies() {
    print_step "Checking dependencies..."
    
    # Check if pacman is available
    if ! command -v pacman &> /dev/null; then
        print_error "pacman not found. Are you sure this is Arch Linux?"
        exit 1
    fi
    
    # Check if required packages are already installed
    local packages=("sdl2" "sdl2_image" "gcc" "make" "pkg-config" "xdg-utils")
    local missing_packages=()
    
    for package in "${packages[@]}"; do
        if ! pacman -Q "$package" &> /dev/null; then
            missing_packages+=("$package")
        fi
    done
    
    if [ ${#missing_packages[@]} -eq 0 ]; then
        print_success "All dependencies are already installed"
        return 0
    fi
    
    print_step "Installing missing dependencies: ${missing_packages[*]}"
    
    # Update package database
    print_step "Updating package database..."
    sudo pacman -Sy
    
    # Install required packages
    print_step "Installing SDL2 libraries..."
    sudo pacman -S --needed "${missing_packages[@]}"
    
    print_success "Dependencies installed successfully"
}

build_imageviewer() {
    print_step "Building imageviewer..."
    
    # Check if we're in the right directory
    if [[ ! -f "main.c" ]] || [[ ! -f "Makefile" ]]; then
        print_error "main.c or Makefile not found. Please run this script from the imageViewer directory."
        exit 1
    fi
    
    # Clean any previous builds
    make clean 2>/dev/null || true
    
    # Build the project
    if make; then
        print_success "Build completed successfully"
    else
        print_error "Build failed"
        exit 1
    fi
    
    # Verify the binary was created
    if [[ ! -f "imageviewer" ]]; then
        print_error "imageviewer binary not found after build"
        exit 1
    fi
    
    print_success "imageviewer binary created"
}

install_binary() {
    print_step "Installing imageviewer to ${INSTALL_DIR}..."
    
    # Create install directory if it doesn't exist
    sudo mkdir -p "${INSTALL_DIR}"
    
    # Copy the binary
    sudo cp imageviewer "${INSTALL_DIR}/"
    sudo chmod +x "${INSTALL_DIR}/imageviewer"
    
    print_success "imageviewer installed to ${INSTALL_DIR}/imageviewer"
}

create_desktop_entry() {
    print_step "Creating desktop entry..."
    
    # Create applications directory if it doesn't exist
    sudo mkdir -p "${DESKTOP_FILE_DIR}"
    
    # Create desktop file
    sudo tee "${DESKTOP_FILE_DIR}/imageviewer.desktop" > /dev/null << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Image Viewer
Comment=Simple SDL2-based image viewer
Exec=imageviewer %f
Icon=imageviewer
Terminal=false
MimeType=image/jpeg;image/jpg;image/png;image/bmp;image/gif;image/tiff;image/tif;image/webp;
Categories=Graphics;Photography;Viewer;
StartupNotify=true
NoDisplay=false
EOF

    print_success "Desktop entry created"
}

create_simple_icon() {
    print_step "Creating application icon..."
    
    # Create icon directory if it doesn't exist
    sudo mkdir -p "${ICON_DIR}"
    
    # Create a simple text-based icon (SVG)
    sudo tee "${ICON_DIR}/imageviewer.svg" > /dev/null << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<svg width="48" height="48" viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg">
  <rect width="48" height="48" fill="#2E3440" rx="4"/>
  <rect x="6" y="6" width="36" height="36" fill="#3B4252" rx="2"/>
  <rect x="10" y="10" width="28" height="20" fill="#4C566A" rx="1"/>
  <circle cx="16" cy="18" r="3" fill="#EBCB8B"/>
  <polygon points="10,25 18,17 22,21 30,13 38,21 38,30 10,30" fill="#81A1C1"/>
  <rect x="10" y="32" width="28" height="6" fill="#5E81AC" rx="1"/>
</svg>
EOF

    print_success "Application icon created"
}

update_desktop_database() {
    print_step "Updating desktop database..."
    
    if command -v update-desktop-database &> /dev/null; then
        sudo update-desktop-database "${DESKTOP_FILE_DIR}" 2>/dev/null || true
        print_success "Desktop database updated"
    else
        print_warning "update-desktop-database not found, skipping..."
    fi
}

set_default_image_viewer() {
    print_step "Setting imageviewer as default image viewer..."
    
    # List of MIME types for images
    local mime_types=(
        "image/jpeg"
        "image/jpg" 
        "image/png"
        "image/bmp"
        "image/gif"
        "image/tiff"
        "image/tif"
        "image/webp"
    )
    
    # Set default application for each MIME type
    for mime_type in "${mime_types[@]}"; do
        if command -v xdg-mime &> /dev/null; then
            xdg-mime default imageviewer.desktop "$mime_type" 2>/dev/null || true
        fi
    done
    
    # Also update MIME database if available
    if command -v update-mime-database &> /dev/null; then
        sudo update-mime-database /usr/share/mime 2>/dev/null || true
    fi
    
    print_success "imageviewer set as default image viewer"
}

test_installation() {
    print_step "Testing installation..."
    
    # Check if binary is in PATH
    if command -v imageviewer &> /dev/null; then
        print_success "imageviewer is available in PATH"
        
        # Show version/help
        echo -e "${BLUE}Running imageviewer --help equivalent:${NC}"
        echo "Usage: imageviewer <image_file_or_directory>"
        echo "Supported formats: JPG, JPEG, PNG, BMP, GIF, TIF"
        
        # Test default application association
        if command -v xdg-mime &> /dev/null; then
            local default_app=$(xdg-mime query default image/jpeg 2>/dev/null)
            if [[ "$default_app" == "imageviewer.desktop" ]]; then
                print_success "imageviewer is set as default image viewer"
            else
                print_warning "Default image viewer association may not have been set correctly"
            fi
        fi
        
    else
        print_error "imageviewer not found in PATH. Installation may have failed."
        exit 1
    fi
}

cleanup() {
    print_step "Cleaning up build files..."
    make clean 2>/dev/null || true
    print_success "Cleanup completed"
}

show_usage_info() {
    echo
    echo -e "${GREEN}Installation completed successfully!${NC}"
    echo
    echo -e "${BLUE}Usage:${NC}"
    echo "  imageviewer <image_file_or_directory>"
    echo "  Or simply double-click on image files (now set as default viewer)"
    echo
    echo -e "${BLUE}Examples:${NC}"
    echo "  imageviewer photo.jpg"
    echo "  imageviewer /path/to/image/directory"
    echo
    echo -e "${BLUE}Controls:${NC}"
    echo "  Mouse wheel / +/-     : Zoom in/out"
    echo "  Mouse drag           : Pan image"
    echo "  Left/Right Arrow     : Navigate between images"
    echo "  Hold Left/Right      : Auto-navigate"
    echo "  R                    : Reset zoom and position"
    echo "  F                    : Fit image to window"
    echo "  H                    : Show help"
    echo "  ESC/Q                : Quit"
    echo
    echo -e "${BLUE}Default Image Viewer:${NC}"
    echo "  imageviewer is now set as the default application for:"
    echo "  JPG, JPEG, PNG, BMP, GIF, TIFF, TIF, WEBP files"
    echo
    echo -e "${BLUE}Uninstall:${NC}"
    echo "  To remove imageviewer, run:"
    echo "  sudo rm ${INSTALL_DIR}/imageviewer"
    echo "  sudo rm ${DESKTOP_FILE_DIR}/imageviewer.desktop"
    echo "  sudo rm ${ICON_DIR}/imageviewer.svg"
}

main() {
    echo -e "${BLUE}ImageViewer Installation Script for Arch Linux${NC}"
    echo "=============================================="
    echo
    
    check_arch
    check_permissions
    
    # Show what the script will do
    echo -e "${YELLOW}This script will:${NC}"
    echo "  1. Install SDL2 dependencies via pacman"
    echo "  2. Build the imageviewer from source"
    echo "  3. Install the binary to ${INSTALL_DIR}"
    echo "  4. Create a desktop entry"
    echo "  5. Set imageviewer as default image viewer"
    echo
    
    install_dependencies
    build_imageviewer
    install_binary
    create_desktop_entry
    create_simple_icon
    update_desktop_database
    set_default_image_viewer
    test_installation
    cleanup
    show_usage_info
}

# Run main function
main "$@"
