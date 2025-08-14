#!/usr/bin/env bash
# Detect GPU vendor and (if NVIDIA) install required driver packages.
# Exports GPU_VENDOR and SKIP_NVIDIA_PACKAGES variables for caller scripts.
set -e

GPU_VENDOR="unknown"

# Get all display / 3D / VGA controllers
PCI_GPU_INFO=$(lspci -nn | grep -Ei 'vga|3d|display' || true)

if echo "$PCI_GPU_INFO" | grep -qi nvidia; then
    GPU_VENDOR="nvidia"
elif echo "$PCI_GPU_INFO" | grep -Eqi 'amd|advanced micro devices|ati'; then
    GPU_VENDOR="amd"
elif echo "$PCI_GPU_INFO" | grep -qi intel; then
    GPU_VENDOR="intel"
fi

export GPU_VENDOR

NVIDIA_PACKAGES=(nvidia nvidia-utils lib32-nvidia-utils)

if [ "$GPU_VENDOR" = "nvidia" ]; then
    echo "Detected NVIDIA GPU. Ensuring NVIDIA packages are installed."
    for pkg in "${NVIDIA_PACKAGES[@]}"; do
        if pacman -Qi "$pkg" >/dev/null 2>&1; then
            echo "  $pkg already installed"
        else
            echo "  Installing $pkg"
            yes | sudo pacman -Sy --noconfirm "$pkg"
        fi
    done
    export SKIP_NVIDIA_PACKAGES="false"
else
    echo "Detected GPU vendor: $GPU_VENDOR (not NVIDIA). Skipping NVIDIA driver installation."
    # If any NVIDIA packages are present, remove them.
    to_remove=()
    for pkg in "${NVIDIA_PACKAGES[@]}"; do
        if pacman -Qi "$pkg" >/dev/null 2>&1; then
            to_remove+=("$pkg")
        fi
    done
    if [ ${#to_remove[@]} -gt 0 ]; then
        echo "Removing NVIDIA specific packages: ${to_remove[*]}"
        # Use --noconfirm and Rns to remove packages with their unused deps.
        yes | sudo pacman -Rns --noconfirm "${to_remove[@]}" || true
    else
        echo "No NVIDIA packages installed to remove."
    fi
    export SKIP_NVIDIA_PACKAGES="true"
fi
