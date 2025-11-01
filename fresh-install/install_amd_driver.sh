#!/usr/bin/env bash
# AMD GPU installation & configuration script (Open source focus per Arch Wiki)
# Expects GPU_VENDOR=amd (set by detect_gpu.sh)
# Environment overrides:
#   AMD_INSTALL_XF86=1            # install xf86-video-amdgpu (default 0)
#   AMD_INSTALL_AMDVLK=1          # also install amdvlk (default 0)
#   AMD_INSTALL_LIB32=1           # force install 32-bit libs even if multilib not detected (default 0)
#   AMD_USE_MESA_GIT=1            # use mesa-git / lib32-mesa-git (AUR) instead of repo mesa
#   AMD_USE_VULKAN_GIT=1          # use vulkan-radeon-git instead of vulkan-radeon
#   AMD_ENABLE_SI_CIK=auto|1|0    # auto (default) enable amdgpu for SI/CIK if detected
#   AMD_SKIP_INITRAMFS=1          # do not regenerate initramfs automatically
#   AMD_VERBOSE=1                 # verbose output
set -e

[ "${GPU_VENDOR}" = "amd" ] || {
  echo "AMD installer invoked but GPU_VENDOR=${GPU_VENDOR}"
  exit 0
}

AMD_INSTALL_XF86=${AMD_INSTALL_XF86:-0}
AMD_INSTALL_AMDVLK=${AMD_INSTALL_AMDVLK:-0}
AMD_INSTALL_LIB32=${AMD_INSTALL_LIB32:-0}
AMD_USE_MESA_GIT=${AMD_USE_MESA_GIT:-0}
AMD_USE_VULKAN_GIT=${AMD_USE_VULKAN_GIT:-0}
AMD_ENABLE_SI_CIK=${AMD_ENABLE_SI_CIK:-auto}
AMD_SKIP_INITRAMFS=${AMD_SKIP_INITRAMFS:-0}
AMD_VERBOSE=${AMD_VERBOSE:-0}

vlog() { [ "$AMD_VERBOSE" = 1 ] && echo "[amd] $*" || true; }
info() { echo "[amd] $*"; }
warn() { echo "[amd][warn] $*" >&2; }

# Detect multilib enabled
if grep -q '^\[multilib\]' /etc/pacman.conf; then
  MULTILIB_ENABLED=1
else
  MULTILIB_ENABLED=0
fi

# Basic packages
BASE_PKGS=(mesa)
[ "$AMD_USE_MESA_GIT" = 1 ] && BASE_PKGS=(mesa-git)

VULKAN_PKG="vulkan-radeon"
[ "$AMD_USE_VULKAN_GIT" = 1 ] && VULKAN_PKG="vulkan-radeon-git"

XF86_PKG="xf86-video-amdgpu"

# 32-bit packages
LIB32_BASE=(lib32-mesa)
[ "$AMD_USE_MESA_GIT" = 1 ] && LIB32_BASE=(lib32-mesa-git)
LIB32_VULKAN_PKG="lib32-vulkan-radeon"
[ "$AMD_USE_VULKAN_GIT" = 1 ] && LIB32_VULKAN_PKG="lib32-vulkan-radeon-git"

# Optional AMDVLK packages
AMDVLK_PKG="amdvlk"
LIB32_AMDVLK_PKG="lib32-amdvlk"

# Simple AUR builder (reused from NVIDIA script style)
_build_aur_pkg() {
  local pkg="$1"
  local url="https://aur.archlinux.org/${pkg}.git"
  mkdir -p "$HOME/aur"
  cd "$HOME/aur"
  if [ ! -d "$pkg" ]; then git clone "$url"; else (cd "$pkg" && git fetch -q --all && git reset -q --hard origin/HEAD || git pull --ff-only || true); fi
  cd "$pkg"
  rm -f -- *.pkg.tar.* 2> /dev/null || true
  yes | makepkg -s -c -C --noconfirm --needed
  local built=(*.pkg.tar.zst)
  yes | sudo pacman -U --noconfirm "${built[@]}"
}

_install_repo_or_aur() {
  local pkg="$1"
  if pacman -Si "$pkg" > /dev/null 2>&1; then
    if pacman -Qi "$pkg" > /dev/null 2>&1; then
      vlog "$pkg already installed"
    else
      yes | sudo pacman -Sy --noconfirm "$pkg"
    fi
  else
    info "Building AUR package: $pkg"
    _build_aur_pkg "$pkg"
  fi
}

info "Installing AMD GPU stack"
for p in "${BASE_PKGS[@]}" "$VULKAN_PKG"; do _install_repo_or_aur "$p"; done

if [ "$AMD_INSTALL_XF86" = 1 ]; then
  _install_repo_or_aur "$XF86_PKG"
fi

# AMDVLK optional (install after vulkan-radeon if requested)
if [ "$AMD_INSTALL_AMDVLK" = 1 ]; then
  _install_repo_or_aur "$AMDVLK_PKG"
fi

if [ $MULTILIB_ENABLED = 1 ] || [ "$AMD_INSTALL_LIB32" = 1 ]; then
  for p in "${LIB32_BASE[@]}" "$LIB32_VULKAN_PKG"; do _install_repo_or_aur "$p"; done
  if [ "$AMD_INSTALL_AMDVLK" = 1 ]; then _install_repo_or_aur "$LIB32_AMDVLK_PKG"; fi
else
  vlog "Skipping 32-bit packages (multilib disabled)"
fi

# Detect SI / CIK codename presence for optional amdgpu enablement
GPU_LINES=$(lspci -nn | grep -Ei 'vga|3d|display' | grep -iE 'amd|ati' || true)
SI_NAMES=(Tahiti Pitcairn Cape Verde Oland Hainan Curacao)
CIK_NAMES=(Bonaire Hawaii Kabini Kaveri Mullins Temash Spectre Spooky)
IS_SI=0
IS_CIK=0
for n in "${SI_NAMES[@]}"; do echo "$GPU_LINES" | grep -q "$n" && IS_SI=1 && break; done
for n in "${CIK_NAMES[@]}"; do echo "$GPU_LINES" | grep -q "$n" && IS_CIK=1 && break; done

if [ "$AMD_ENABLE_SI_CIK" = "1" ] || { [ "$AMD_ENABLE_SI_CIK" = "auto" ] && { [ $IS_SI = 1 ] || [ $IS_CIK = 1 ]; }; }; then
  info "Configuring amdgpu for SI/CIK (IS_SI=$IS_SI IS_CIK=$IS_CIK)"
  TMP_CONF=$(mktemp)
  printf 'options amdgpu si_support=1\noptions amdgpu cik_support=1\n' > "$TMP_CONF"
  printf 'options radeon si_support=0\noptions radeon cik_support=0\n' >> "$TMP_CONF"
  sudo mkdir -p /etc/modprobe.d
  sudo cp "$TMP_CONF" /etc/modprobe.d/10-amdgpu-si-cik.conf
  rm -f "$TMP_CONF"
  # Ensure amdgpu early in MODULES
  if [ -f /etc/mkinitcpio.conf ]; then
    if ! grep -q '^MODULES=.*amdgpu' /etc/mkinitcpio.conf; then
      sudo sed -i 's/^MODULES=\(.*\)/MODULES=(amdgpu radeon)/' /etc/mkinitcpio.conf || true
    fi
    if ! grep -q 'modconf' /etc/mkinitcpio.conf; then
      warn "modconf hook not found in mkinitcpio.conf (needed for module options)"
    fi
    if [ "$AMD_SKIP_INITRAMFS" != 1 ]; then
      info "Regenerating initramfs (mkinitcpio -P)"
      sudo mkinitcpio -P || warn "mkinitcpio failed; review manually"
    else
      info "Skipping initramfs regeneration per AMD_SKIP_INITRAMFS=1"
    fi
  else
    warn "/etc/mkinitcpio.conf not found; skipping MODULES update"
  fi
else
  vlog "SI/CIK enablement not required (AMD_ENABLE_SI_CIK=$AMD_ENABLE_SI_CIK IS_SI=$IS_SI IS_CIK=$IS_CIK)"
fi

# Check active kernel driver
KDRV=$(lspci -k -d ::0300 2> /dev/null | awk '/Kernel driver in use:/ {print $5; exit}')
[ -z "$KDRV" ] && KDRV=$(lsmod | grep -E 'amdgpu|radeon' | head -n1 | awk '{print $1}')
info "Kernel driver in use: ${KDRV:-unknown}"

if [ "$KDRV" = "radeon" ] && { [ $IS_SI = 1 ] || [ $IS_CIK = 1 ]; }; then
  warn "radeon driver still active for SI/CIK; reboot may be required to switch to amdgpu"
fi

export AMD_STACK_DONE=1
info "AMD GPU stack installation complete"
