#!/usr/bin/env bash
# Intel GPU installation & configuration script (open source stack)
# Expects GPU_VENDOR=intel
# Environment overrides:
#   INTEL_USE_AMBER=0/1          # use mesa-amber instead of mesa (legacy Gen2-11 classic drivers)
#   INTEL_INSTALL_LIB32=auto/1/0 # install 32-bit libs (auto: only if multilib enabled) default auto
#   INTEL_INSTALL_VULKAN=1/0     # install vulkan-intel (default 1)
#   INTEL_INSTALL_LIB32_VK=auto/1/0 # 32-bit vulkan driver (auto: if 32-bit mesa installed) default auto
#   INTEL_INSTALL_XF86=0/1       # install xf86-video-intel legacy DDX (default 0, not recommended)
#   INTEL_ENABLE_GUC=            # empty (do nothing) or 0/1/2/3 value to set enable_guc= kernel param
#   INTEL_SKIP_INITRAMFS=0/1     # skip mkinitcpio regeneration (default 0)
#   INTEL_VERBOSE=0/1            # verbose logging
set -e

[ "$GPU_VENDOR" = "intel" ] || { echo "Intel installer invoked but GPU_VENDOR=$GPU_VENDOR"; exit 0; }

INTEL_USE_AMBER=${INTEL_USE_AMBER:-0}
INTEL_INSTALL_LIB32=${INTEL_INSTALL_LIB32:-auto}
INTEL_INSTALL_VULKAN=${INTEL_INSTALL_VULKAN:-1}
INTEL_INSTALL_LIB32_VK=${INTEL_INSTALL_LIB32_VK:-auto}
INTEL_INSTALL_XF86=${INTEL_INSTALL_XF86:-0}
INTEL_ENABLE_GUC=${INTEL_ENABLE_GUC:-}
INTEL_SKIP_INITRAMFS=${INTEL_SKIP_INITRAMFS:-0}
INTEL_VERBOSE=${INTEL_VERBOSE:-1}

vlog() { [ "$INTEL_VERBOSE" = 1 ] && echo "[intel] $*" || true; }
info() { echo "[intel] $*"; }
warn() { echo "[intel][warn] $*" >&2; }

# Detect multilib
if grep -q '^\[multilib\]' /etc/pacman.conf; then MULTILIB=1; else MULTILIB=0; fi

# Base mesa package
if [ "$INTEL_USE_AMBER" = 1 ]; then
  BASE_MESA=mesa-amber
  LIB32_BASE=lib32-mesa-amber
else
  BASE_MESA=mesa
  LIB32_BASE=lib32-mesa
fi

install_pkg() {
  local pkg="$1"
  if pacman -Qi "$pkg" >/dev/null 2>&1; then
    vlog "$pkg already installed"
  else
    if pacman -Si "$pkg" >/dev/null 2>&1; then
      yes | sudo pacman -Sy --noconfirm "$pkg"
    else
      warn "Package $pkg not found in repos (not handling AUR here)"
    fi
  fi
}

info "Installing Intel GPU stack"
install_pkg "$BASE_MESA"

# 32-bit mesa
if { [ "$INTEL_INSTALL_LIB32" = auto ] && [ $MULTILIB = 1 ]; } || [ "$INTEL_INSTALL_LIB32" = 1 ]; then
  install_pkg "$LIB32_BASE"
else
  vlog "Skipping 32-bit mesa (INTEL_INSTALL_LIB32=$INTEL_INSTALL_LIB32 MULTILIB=$MULTILIB)"
fi

# Vulkan
if [ "$INTEL_INSTALL_VULKAN" = 1 ]; then
  install_pkg vulkan-intel
  if { [ "$INTEL_INSTALL_LIB32_VK" = auto ] && [ $MULTILIB = 1 ]; } || [ "$INTEL_INSTALL_LIB32_VK" = 1 ]; then
    install_pkg lib32-vulkan-intel
  else
    vlog "Skipping 32-bit vulkan (INTEL_INSTALL_LIB32_VK=$INTEL_INSTALL_LIB32_VK MULTILIB=$MULTILIB)"
  fi
fi

# Legacy xf86-video-intel (not recommended)
if [ "$INTEL_INSTALL_XF86" = 1 ]; then
  install_pkg xf86-video-intel
else
  vlog "Not installing xf86-video-intel (INTEL_INSTALL_XF86=$INTEL_INSTALL_XF86)"
fi

# GuC / HuC enablement
if [ -n "$INTEL_ENABLE_GUC" ]; then
  if ! echo "$INTEL_ENABLE_GUC" | grep -Eq '^[0-3]$'; then
    warn "INTEL_ENABLE_GUC must be 0..3; ignoring"
  else
    info "Configuring enable_guc=$INTEL_ENABLE_GUC"
    sudo mkdir -p /etc/modprobe.d
    echo "options i915 enable_guc=$INTEL_ENABLE_GUC" | sudo tee /etc/modprobe.d/i915-guc.conf >/dev/null
    if [ "$INTEL_SKIP_INITRAMFS" != 1 ] && [ -f /etc/mkinitcpio.conf ]; then
      info "Regenerating initramfs (mkinitcpio -P) for GuC/HuC change"
      sudo mkinitcpio -P || warn "mkinitcpio failed; continue manually"
    else
      info "Skipping initramfs regeneration (INTEL_SKIP_INITRAMFS=$INTEL_SKIP_INITRAMFS)"
    fi
  fi
fi

# Report kernel driver
KDRV=$(lspci -k -d ::0300 2>/dev/null | awk '/Kernel driver in use:/ {print $5; exit}')
[ -z "$KDRV" ] && KDRV=$(lsmod | grep -E 'i915|xe' | head -n1 | awk '{print $1}')
info "Kernel driver in use: ${KDRV:-unknown}"

info "Intel GPU stack installation complete"
export INTEL_STACK_DONE=1
