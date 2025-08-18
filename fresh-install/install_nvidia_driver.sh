#!/usr/bin/env bash
# NVIDIA driver selection & installation (split from detect script)
# Expects GPU_VENDOR=nvidia
# Outputs: NVIDIA_DRIVER_PACKAGE
set -e

[ "$GPU_VENDOR" = "nvidia" ] || { echo "NVIDIA installer invoked but GPU_VENDOR=$GPU_VENDOR"; exit 0; }

_build_aur_pkg() {
  local pkg="$1"; local repo_url="https://aur.archlinux.org/${pkg}.git";
  mkdir -p "$HOME/aur"; cd "$HOME/aur";
  if [ ! -d "$pkg" ]; then git clone "$repo_url"; else (cd "$pkg" && git fetch -q --all && git reset -q --hard origin/HEAD || git pull --ff-only || true); fi
  cd "$pkg"; rm -f -- *.pkg.tar.* 2>/dev/null || true
  yes | makepkg -s -c -C --noconfirm --needed || return 1
  local built=( *.pkg.tar.zst ); yes | sudo pacman -U --noconfirm "${built[@]}"
}

_choose_nvidia_pkg() {
  local have_linux have_linux_lts multiple_kernels driver_pkg prefer_open detect_out legacy_detected=0
  prefer_open=${NVIDIA_PREFER_OPEN:-1}
  pacman -Qq | grep -qx linux && have_linux=1 || have_linux=0
  pacman -Qq | grep -qx linux-lts && have_linux_lts=1 || have_linux_lts=0
  if [ $((have_linux + have_linux_lts)) -gt 1 ]; then multiple_kernels=1; else multiple_kernels=0; fi

  # Optionally skip attempting to install nvidia-detect (some minimal repo setups don't have it yet)
  if [ -z "${NVIDIA_SKIP_DETECT:-}" ] && ! command -v nvidia-detect >/dev/null 2>&1; then
    if pacman -Si nvidia-detect >/dev/null 2>&1; then
      echo "Attempting to install helper utility: nvidia-detect" >&2
      # Use --needed to avoid forcing refresh (& avoid partial upgrade semantics with -Sy)
      yes | sudo pacman -S --needed --noconfirm nvidia-detect || echo "nvidia-detect install failed (continuing with heuristic)" >&2
    else
      echo "nvidia-detect not present in enabled repos; using heuristic selection." >&2
    fi
  fi

  if command -v nvidia-detect >/dev/null 2>&1; then
    detect_out="$(nvidia-detect 2>/dev/null || true)"
  fi

  if [ -n "$detect_out" ]; then
    if echo "$detect_out" | grep -q '470'; then driver_pkg='nvidia-470xx-dkms'; legacy_detected=1; fi
    if echo "$detect_out" | grep -q '390'; then driver_pkg='nvidia-390xx-dkms'; legacy_detected=1; fi
    if echo "$detect_out" | grep -q '340'; then driver_pkg='nvidia-340xx-dkms'; legacy_detected=1; fi
  fi

  if [ "$legacy_detected" = 0 ]; then
    # Heuristic modern driver selection
    if [ "$multiple_kernels" = 1 ]; then
      if [ "$prefer_open" = 1 ] && pacman -Si nvidia-open-dkms >/dev/null 2>&1; then driver_pkg='nvidia-open-dkms'; else driver_pkg='nvidia-dkms'; fi
    else
      if [ "$have_linux_lts" = 1 ] && [ "$have_linux" = 0 ]; then
        if [ "$prefer_open" = 1 ] && pacman -Si nvidia-open-lts >/dev/null 2>&1; then driver_pkg='nvidia-open-lts'; else driver_pkg='nvidia-lts'; fi
      else
        if [ "$prefer_open" = 1 ] && pacman -Si nvidia-open >/dev/null 2>&1; then driver_pkg='nvidia-open'; else driver_pkg='nvidia'; fi
      fi
    fi
  else
    echo "Legacy NVIDIA generation detected via nvidia-detect output; choosing $driver_pkg" >&2
  fi

  echo "$driver_pkg"
}

_remove_conflicting_nvidia_pkgs() {
  local keep="$1"; local candidates=(nvidia nvidia-lts nvidia-dkms nvidia-open nvidia-open-lts nvidia-open-dkms nvidia-470xx-dkms nvidia-390xx-dkms nvidia-340xx-dkms)
  local to_remove=()
  for p in "${candidates[@]}"; do
    if pacman -Qi "$p" >/dev/null 2>&1 && [ "$p" != "$keep" ]; then to_remove+=("$p"); fi
  done
  if [ ${#to_remove[@]} -gt 0 ]; then yes | sudo pacman -Rns --noconfirm "${to_remove[@]}" || true; fi
}

_install_nvidia_stack() {
  local driver_pkg="$1"
  if [[ "$driver_pkg" == nvidia-*xx-dkms ]]; then _build_aur_pkg "$driver_pkg"; else yes | sudo pacman -Sy --noconfirm "$driver_pkg"; fi
  local utils_pkg="nvidia-utils" utils32_pkg="lib32-nvidia-utils"
  if ! pacman -Qi "$utils_pkg" >/dev/null 2>&1; then yes | sudo pacman -Sy --noconfirm "$utils_pkg"; fi
  if grep -q '^\[multilib\]' /etc/pacman.conf; then
    if ! pacman -Qi "$utils32_pkg" >/dev/null 2>&1; then yes | sudo pacman -Sy --noconfirm "$utils32_pkg" || true; fi
  fi
}

echo "Detected NVIDIA GPU. Selecting driver..."
NVIDIA_DRIVER_PACKAGE=$(_choose_nvidia_pkg)
export NVIDIA_DRIVER_PACKAGE
_remove_conflicting_nvidia_pkgs "$NVIDIA_DRIVER_PACKAGE"
_install_nvidia_stack "$NVIDIA_DRIVER_PACKAGE"
export SKIP_NVIDIA_PACKAGES="false"
echo "NVIDIA driver installation finished (package: $NVIDIA_DRIVER_PACKAGE)"
echo "Optional: adjust /etc/mkinitcpio.conf (remove kms) then: sudo mkinitcpio -P"
