#!/bin/bash
# Linter installation: command probes, Arch/AUR detection, and the pacman /
# AUR-helper dispatch for shellcheck, shfmt, checkbashisms and bashate.
#
# Sourced by shell_check.sh; split out to keep it under the 250-line cap.
# Sourced rather than run, so it inherits the caller's options and reads
# SKIP_INSTALL and VERBOSE, which the entry sets from its arguments above the
# source line.

is_cmd() { command -v "$1" > /dev/null 2>&1; }

is_arch() { is_cmd pacman; }
have_aur_helper() { is_cmd yay || is_cmd paru; }

install_if_missing() {
  local pkg cmd
  pkg="$1"
  cmd="$2"
  if is_cmd "$cmd"; then
    [[ $VERBOSE == "true" ]] && log_info "Found $cmd"
    return 0
  fi

  if [[ $SKIP_INSTALL == "true" ]]; then
    log_warn "Skipping install of $pkg ($cmd not found)"
    return 1
  fi

  if is_arch; then
    log_info "Installing $pkg via pacman..."
    if ! sudo pacman -S --needed --noconfirm "$pkg"; then
      log_warn "Failed to install $pkg via pacman."
      return 1
    fi
    return 0
  else
    log_warn "Non-Arch system detected. Please install '$pkg' manually."
    return 1
  fi
}

install_linters() {
  local ok=0

  # Core linters
  install_if_missing shellcheck shellcheck || ok=1
  install_if_missing shfmt shfmt || ok=1

  # Optional linters (best-effort)
  # checkbashisms may be in repos or AUR; try pacman first, then AUR helper
  if ! is_cmd checkbashisms; then
    if is_arch; then
      if ! sudo pacman -S --needed --noconfirm checkbashisms 2> /dev/null; then
        if have_aur_helper; then
          log_info "Installing checkbashisms from AUR (requires yay/paru)..."
          if is_cmd yay; then yay -S --noconfirm checkbashisms || true; fi
          if is_cmd paru; then paru -S --noconfirm checkbashisms || true; fi
        else
          log_warn "checkbashisms not installed (no AUR helper)."
        fi
      fi
    fi
  fi

  # bashate (python-based), typically available as python-bashate in AUR
  if ! is_cmd bashate; then
    if is_arch && have_aur_helper; then
      log_info "Installing bashate from AUR (requires yay/paru)..."
      if is_cmd yay; then yay -S --noconfirm python-bashate || true; fi
      if is_cmd paru; then paru -S --noconfirm python-bashate || true; fi
    else
      # Try pip if user has it and wants to
      if is_cmd pipx; then
        log_info "Installing bashate via pipx..."
        pipx install bashate || true
      elif is_cmd pip3; then
        log_info "Installing bashate via pip (user)..."
        pip3 install --user bashate || true
      else
        log_warn "bashate not installed (no AUR helper or pip available)."
      fi
    fi
  fi

  return "$ok"
}
