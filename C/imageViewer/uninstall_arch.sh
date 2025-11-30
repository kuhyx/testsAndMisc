#!/bin/bash

# ImageViewer Uninstallation Script for Arch Linux

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

remove_files() {
    print_step "Removing imageviewer files..."

    # Remove binary
    if [[ -f "${INSTALL_DIR}/imageviewer" ]]; then
        sudo rm "${INSTALL_DIR}/imageviewer"
        print_success "Removed ${INSTALL_DIR}/imageviewer"
    else
        print_warning "Binary not found at ${INSTALL_DIR}/imageviewer"
    fi

    # Remove desktop entry
    if [[ -f "${DESKTOP_FILE_DIR}/imageviewer.desktop" ]]; then
        sudo rm "${DESKTOP_FILE_DIR}/imageviewer.desktop"
        print_success "Removed desktop entry"
    else
        print_warning "Desktop entry not found"
    fi

    # Remove icon
    if [[ -f "${ICON_DIR}/imageviewer.svg" ]]; then
        sudo rm "${ICON_DIR}/imageviewer.svg"
        print_success "Removed application icon"
    else
        print_warning "Application icon not found"
    fi
}

reset_default_associations() {
    print_step "Resetting default image viewer associations..."

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

    # Reset default application for each MIME type
    for mime_type in "${mime_types[@]}"; do
        if command -v xdg-mime &> /dev/null; then
            # Check if imageviewer was the default
            local current_default
            current_default=$(xdg-mime query default "$mime_type" 2>/dev/null)
            if [[ "$current_default" == "imageviewer.desktop" ]]; then
                # Remove the association (this will fall back to system defaults)
                local mimeapps_file="$HOME/.config/mimeapps.list"
                if [[ -f "$mimeapps_file" ]]; then
                    sed -i "/^${mime_type}=imageviewer.desktop$/d" "$mimeapps_file" 2>/dev/null || true
                fi
            fi
        fi
    done

    print_success "Default image viewer associations reset"
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

main() {
    echo -e "${BLUE}ImageViewer Uninstallation Script${NC}"
    echo "================================="
    echo

    # Show what will be removed
    echo -e "${YELLOW}This script will remove:${NC}"
    echo "  - ${INSTALL_DIR}/imageviewer"
    echo "  - ${DESKTOP_FILE_DIR}/imageviewer.desktop"
    echo "  - ${ICON_DIR}/imageviewer.svg"
    echo
    echo -e "${YELLOW}Note: Dependencies (SDL2 libraries) will NOT be removed.${NC}"
    echo

    remove_files
    reset_default_associations
    update_desktop_database

    echo
    echo -e "${GREEN}ImageViewer has been successfully uninstalled!${NC}"
    echo
    echo -e "${BLUE}To remove dependencies (if no longer needed):${NC}"
    echo "  sudo pacman -R sdl2 sdl2_image"
}

# Run main function
main "$@"
