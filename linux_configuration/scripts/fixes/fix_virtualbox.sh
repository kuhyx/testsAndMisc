#!/usr/bin/env bash

set -euo pipefail

# Source common library
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
# shellcheck source=../lib/common.sh
source "$SCRIPT_DIR/../lib/common.sh"

on_error() {
  local exit_code=$?
  local line_number=$1
  log_error "Unexpected failure at line ${line_number} (exit code ${exit_code})."
}
trap 'on_error ${LINENO}' ERR

require_pacman() {
  if ! has_cmd pacman; then
    log_error "pacman not found. This script is intended for Arch Linux systems."
    exit 1
  fi
}

detect_kernel_release() {
  uname -r
}

select_host_package() {
  local kernel_release=$1
  case "${kernel_release}" in
    *-lts)
      echo "virtualbox-host-modules-lts"
      ;;
    *-arch*)
      echo "virtualbox-host-modules-arch"
      ;;
    *)
      echo "virtualbox-host-dkms"
      ;;
  esac
}

collect_kernel_headers() {
  local -a headers=()
  local kernel_pkg header_pkg
  for kernel_pkg in linux linux-lts linux-zen linux-hardened; do
    if pacman -Q "${kernel_pkg}" > /dev/null 2>&1; then
      header_pkg="${kernel_pkg}-headers"
      headers+=("${header_pkg}")
    fi
  done
  if [[ ${#headers[@]} -gt 0 ]]; then
    printf '%s\n' "${headers[@]}"
  fi
}

maybe_remove_conflicting_host_packages() {
  local selected_package=$1
  local -a candidates=("virtualbox-host-dkms" "virtualbox-host-modules-arch" "virtualbox-host-modules-lts")
  local pkg
  for pkg in "${candidates[@]}"; do
    if [[ ${pkg} != "${selected_package}" ]] && pacman -Q "${pkg}" > /dev/null 2>&1; then
      log_warn "Removing conflicting package ${pkg} before installing ${selected_package}."
      pacman -Rsn "${PACMAN_REMOVE_FLAGS[@]}" "${pkg}"
    fi
  done
}

install_packages() {
  local -a packages=()
  local -a headers=()
  local host_package=$1
  shift
  if [[ $# -gt 0 ]]; then
    mapfile -t headers < <(printf '%s\n' "$@" | sort -u)
  fi
  packages+=("virtualbox" "virtualbox-guest-iso" "${host_package}")
  if [[ ${host_package} == "virtualbox-host-dkms" ]]; then
    packages+=("dkms")
  fi
  if [[ ${#headers[@]} -gt 0 ]]; then
    packages+=("${headers[@]}")
  fi
  log_info "Installing packages: ${packages[*]}"
  pacman -S "${PACMAN_INSTALL_FLAGS[@]}" "${packages[@]}"
}

rebuild_virtualbox_modules() {
  local host_package=$1
  if [[ ${host_package} == "virtualbox-host-dkms" ]]; then
    if command -v dkms > /dev/null 2>&1; then
      log_info "Rebuilding VirtualBox DKMS modules for all installed kernels."
      dkms autoinstall
    else
      log_warn "dkms command not found; skipping DKMS rebuild."
    fi
  fi
}

reload_virtualbox_modules() {
  log_info "Loading VirtualBox kernel modules."
  if [[ -x /sbin/rcvboxdrv ]]; then
    /sbin/rcvboxdrv setup || log_warn "rcvboxdrv reported an issue while setting up modules."
  elif [[ -x /usr/lib/virtualbox/vboxdrv.sh ]]; then
    /usr/lib/virtualbox/vboxdrv.sh setup || log_warn "vboxdrv.sh reported an issue while setting up modules."
  fi

  local -a modules=(vboxdrv vboxnetflt vboxnetadp vboxpci)
  local mod
  for mod in "${modules[@]}"; do
    if ! lsmod | awk '{print $1}' | grep -Fxq "${mod}"; then
      if ! modprobe "${mod}" > /dev/null 2>&1; then
        log_warn "Module ${mod} failed to load; check dmesg for details."
      fi
    fi
  done

  if ! lsmod | awk '{print $1}' | grep -Fxq "vboxdrv"; then
    log_error "VirtualBox kernel driver (vboxdrv) failed to load. Review /var/log and dmesg output for clues."
  fi
  log_info "VirtualBox kernel driver loaded successfully."
}

warn_if_secure_boot_enabled() {
  local secure_boot_file
  if [[ -d /sys/firmware/efi/efivars ]]; then
    secure_boot_file=$(find /sys/firmware/efi/efivars -maxdepth 1 -name 'SecureBoot-*' -print -quit 2> /dev/null || true)
    if [[ -n ${secure_boot_file} && -r ${secure_boot_file} ]]; then
      local state
      state=$(hexdump -n 1 -s 4 -e '1 "%d"' "${secure_boot_file}" 2> /dev/null || echo "0")
      if [[ ${state} == "1" ]]; then
        log_warn "EFI Secure Boot appears to be enabled. You may need to sign VirtualBox modules manually."
      fi
    fi
  fi
}

remind_group_membership() {
  local invoking_user=${SUDO_USER:-}
  if [[ -n ${invoking_user} && ${invoking_user} != "root" ]]; then
    if ! id -nG "${invoking_user}" | grep -qw "vboxusers"; then
      log_warn "User ${invoking_user} is not in the vboxusers group. Add them with: sudo gpasswd -a ${invoking_user} vboxusers"
    else
      log_info "User ${invoking_user} is already in the vboxusers group."
    fi
  fi
}

main() {
  require_root
  require_pacman

  PACMAN_INSTALL_FLAGS=(--needed)
  PACMAN_REMOVE_FLAGS=()
  if [[ ${PACMAN_CONFIRM:-0} == "1" ]]; then
    log_info "PACMAN_CONFIRM=1 detected; pacman will prompt for confirmation."
  else
    PACMAN_INSTALL_FLAGS+=(--noconfirm)
    PACMAN_REMOVE_FLAGS+=(--noconfirm)
  fi

  local kernel_release host_package
  kernel_release=$(detect_kernel_release)
  log_info "Detected running kernel: ${kernel_release}"
  host_package=$(select_host_package "${kernel_release}")
  log_info "Selected VirtualBox host package: ${host_package}"

  mapfile -t kernel_headers < <(collect_kernel_headers)
  if [[ ${host_package} == "virtualbox-host-dkms" && ${#kernel_headers[@]} -eq 0 ]]; then
    log_warn "No matching kernel headers detected. Ensure you've installed headers for your kernel so DKMS can build modules."
  fi

  maybe_remove_conflicting_host_packages "${host_package}"
  install_packages "${host_package}" "${kernel_headers[@]}"
  rebuild_virtualbox_modules "${host_package}"
  reload_virtualbox_modules
  warn_if_secure_boot_enabled
  remind_group_membership

  log_info "VirtualBox installation and driver setup complete."
}

main "$@"
