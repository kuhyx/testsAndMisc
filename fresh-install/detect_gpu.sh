#!/usr/bin/env bash
# Lightweight GPU detection script.
# Detects GPU vendor and invokes the corresponding vendor install/management script.
# Exports: GPU_VENDOR
set -e

GPU_VENDOR="unknown"
PCI_GPU_INFO=$(lspci -nn | grep -Ei 'vga|3d|display' || true)

if echo "$PCI_GPU_INFO" | grep -qi nvidia; then
    GPU_VENDOR="nvidia"
elif echo "$PCI_GPU_INFO" | grep -Eqi '\b(amd|advanced micro devices|ati)\b'; then
    GPU_VENDOR="amd"
elif echo "$PCI_GPU_INFO" | grep -qi intel; then
    GPU_VENDOR="intel"
fi

export GPU_VENDOR
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

case "$GPU_VENDOR" in
  nvidia)
    if [ -x "$SCRIPT_DIR/install_nvidia_driver.sh" ]; then
      . "$SCRIPT_DIR/install_nvidia_driver.sh"
    else
      echo "NVIDIA installer script missing: $SCRIPT_DIR/install_nvidia_driver.sh"
    fi
    ;;
  amd)
    if [ -x "$SCRIPT_DIR/install_amd_driver.sh" ]; then
      . "$SCRIPT_DIR/install_amd_driver.sh"
    else
      echo "AMD installer script missing: $SCRIPT_DIR/install_amd_driver.sh (placeholder)"
    fi
    ;;
  intel)
    if [ -x "$SCRIPT_DIR/install_intel_driver.sh" ]; then
      . "$SCRIPT_DIR/install_intel_driver.sh"
    else
      echo "Intel installer script missing: $SCRIPT_DIR/install_intel_driver.sh"
    fi
    ;;
  *)
    echo "Unknown / no discrete GPU detected."
    ;;
esac
