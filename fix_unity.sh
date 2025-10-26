#!/usr/bin/env bash

# Fix Unity Hub login on Linux (Arch/XFCE) by ensuring the unityhub:// URL scheme
# is correctly registered and handled. This script:
# - Detects Unity Hub installation type (Native, Flatpak, AppImage)
# - Creates a local desktop entry to handle x-scheme-handler/unityhub (and unity)
# - Registers the handler using xdg-mime and updates desktop database
# - Optionally installs required tools (xdg-utils, desktop-file-utils, portals)
# - Optionally tests the handler by opening a unityhub:// link
#
# Usage:
#   bash Bash/fix_unity.sh                   # Run fix (no deps install, no test)
#   bash Bash/fix_unity.sh -y                # Auto-install deps (Arch) if missing
#   bash Bash/fix_unity.sh --test            # Also launches a test unityhub:// link
#   bash Bash/fix_unity.sh -y --test         # Install deps and run test
#
# Notes:
# - For Flatpak installs, Exec uses: flatpak run com.unity.UnityHub %U
# - For native installs, Exec uses the unityhub binary path with %U
# - Chromium/Thorium may prompt to "Open xdg-open" after web login—allow it.

set -euo pipefail
IFS=$'\n\t'

SCRIPT_NAME="$(basename "$0")"
GREEN="\033[1;32m"; YELLOW="\033[1;33m"; RED="\033[1;31m"; BLUE="\033[1;34m"; NC="\033[0m"

log_info()  { echo -e "${BLUE}[INFO]${NC} $*"; }
log_ok()    { echo -e "${GREEN}[ OK ]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERR ]${NC} $*" 1>&2; }

usage() {
  cat <<EOF
${SCRIPT_NAME} - Fix Unity Hub sign-in by registering unityhub:// URL handler

Options:
  -y, --yes        Auto-install required packages on Arch (sudo pacman)
  --test           After setup, open a test link: unityhub://v1/editor-signin
  -h, --help       Show this help

This script creates ~/.local/share/applications/unityhub-url-handler.desktop
and sets it as the default handler for x-scheme-handler/unityhub (and unity).
EOF
}

AUTO_INSTALL=false
RUN_TEST=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    -y|--yes) AUTO_INSTALL=true; shift ;;
    --test)   RUN_TEST=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) log_error "Unknown argument: $1"; usage; exit 1 ;;
  esac
done

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    return 1
  fi
}

ensure_deps_arch() {
  # Best-effort install for Arch-based systems
  if [[ "$AUTO_INSTALL" != true ]]; then
    log_warn "Skipping package installation (use -y to auto-install)."
    return 0
  fi
  if ! require_cmd pacman; then
    log_warn "Not an Arch-based system (pacman not found). Skipping auto-install."
    return 0
  fi
  local pkgs=(xdg-utils desktop-file-utils xdg-desktop-portal xdg-desktop-portal-gtk)
  log_info "Installing/ensuring packages: ${pkgs[*]}"
  if ! require_cmd sudo; then
    log_warn "sudo not found; attempting pacman directly (may fail)."
    sudo_cmd=""
  else
    sudo_cmd="sudo"
  fi
  # Use --needed to avoid reinstalling
  set +e
  $sudo_cmd pacman -S --needed --noconfirm "${pkgs[@]}"
  local rc=$?
  set -e
  if [[ $rc -ne 0 ]]; then
    log_warn "Package install may have failed or been partial. Continuing anyway."
  else
    log_ok "Dependencies installed/verified."
  fi
}

desktop_dir="$HOME/.local/share/applications"
mkdir -p "$desktop_dir"

detect_unityhub() {
  # Outputs: INSTALL_TYPE (FLATPAK|NATIVE|APPIMAGE|UNKNOWN) and EXEC_CMD
  local install_type="UNKNOWN" exec_cmd=""

  # 1) Flatpak
  if command -v flatpak >/dev/null 2>&1; then
    if flatpak info com.unity.UnityHub >/dev/null 2>&1; then
      install_type="FLATPAK"
      exec_cmd="flatpak run com.unity.UnityHub %U"
      echo "$install_type|$exec_cmd"
      return 0
    fi
  fi

  # 2) Native binary in PATH
  if command -v unityhub >/dev/null 2>&1; then
    local path
    path="$(command -v unityhub)"
    install_type="NATIVE"
    exec_cmd="$path %U"
    echo "$install_type|$exec_cmd"
    return 0
  fi

  # 3) Search desktop files for Unity Hub Exec
  local search_dirs=(
    "$HOME/.local/share/applications"
    "/usr/share/applications"
    "/var/lib/flatpak/exports/share/applications"
    "$HOME/.local/share/flatpak/exports/share/applications"
  )
  local found_exec=""
  for d in "${search_dirs[@]}"; do
    [[ -d "$d" ]] || continue
    # prefer official naming when present
    local f
    for f in "$d"/*.desktop; do
      [[ -e "$f" ]] || continue
      if grep -qiE '^(Name|Comment)=.*Unity Hub' "$f" 2>/dev/null || \
         grep -qiE 'Exec=.*unityhub' "$f" 2>/dev/null; then
        local exec_line
        exec_line="$(grep -iE '^Exec=' "$f" | head -n1 | sed 's/^Exec=//')"
        if [[ -n "$exec_line" ]]; then
          found_exec="$exec_line"
          break 2
        fi
      fi
    done
  done

  if [[ -n "$found_exec" ]]; then
    # Normalize: ensure %U present
    if [[ "$found_exec" != *"%U"* && "$found_exec" != *"%u"* ]]; then
      found_exec+=" %U"
    fi
    if [[ "$found_exec" == flatpak* ]]; then
      install_type="FLATPAK"
    elif [[ "$found_exec" == *AppImage* || "$found_exec" == *appimage* ]]; then
      install_type="APPIMAGE"
    else
      install_type="NATIVE"
    fi
    echo "$install_type|$found_exec"
    return 0
  fi

  # 4) Try common AppImage locations
  local ai_candidates=(
    "$HOME/Applications/UnityHub*.AppImage"
    "$HOME/.local/bin/UnityHub*.AppImage"
    "/opt/UnityHub*/UnityHub*.AppImage"
  )
  local ai
  for ai in "${ai_candidates[@]}"; do
    for p in $ai; do
      if [[ -f "$p" && -x "$p" ]]; then
        install_type="APPIMAGE"
        exec_cmd="$p %U"
        echo "$install_type|$exec_cmd"
        return 0
      fi
    done
  done

  echo "$install_type|$exec_cmd"
}

create_handler_desktop() {
  local exec_cmd="$1"
  local dest="$desktop_dir/unityhub-url-handler.desktop"
  log_info "Writing handler desktop entry: $dest"
  cat > "$dest" <<DESK
[Desktop Entry]
Name=Unity Hub URL Handler
Comment=Handle unityhub:// links for Unity Hub sign-in
Exec=${exec_cmd}
Terminal=false
Type=Application
Icon=unityhub
Categories=Development;
StartupWMClass=Unity Hub
MimeType=x-scheme-handler/unityhub;x-scheme-handler/unity;
NoDisplay=true
DESK
  log_ok "Desktop entry created/updated."
  echo "$dest"
}

register_mime_handler() {
  local desktop_file="$1"
  # Update desktop database if available
  if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$desktop_dir" || true
  else
    log_warn "update-desktop-database not found (install desktop-file-utils)."
  fi

  # Register as default handler for both schemes
  if command -v xdg-mime >/dev/null 2>&1; then
    xdg-mime default "$(basename "$desktop_file")" x-scheme-handler/unityhub || true
    xdg-mime default "$(basename "$desktop_file")" x-scheme-handler/unity || true
  else
    log_error "xdg-mime not found (install xdg-utils)."
    return 1
  fi
  log_ok "MIME handler registered for unityhub:// (and unity://)."
}

verify_registration() {
  local expected="$(basename "$1")"
  local cur1="$(xdg-mime query default x-scheme-handler/unityhub 2>/dev/null || true)"
  local cur2="$(xdg-mime query default x-scheme-handler/unity 2>/dev/null || true)"
  log_info "Current handler (unityhub): ${cur1:-<none>}"
  log_info "Current handler (unity):    ${cur2:-<none>}"
  if [[ "$cur1" == "$expected" ]]; then
    log_ok "unityhub scheme correctly set to $expected"
  else
    log_warn "unityhub scheme not set to $expected (currently: ${cur1:-none})."
  fi
}

maybe_test_open() {
  if [[ "$RUN_TEST" == true ]]; then
    log_info "Opening test link: unityhub://v1/editor-signin"
    if command -v xdg-open >/dev/null 2>&1; then
      xdg-open 'unityhub://v1/editor-signin' >/dev/null 2>&1 || true
      log_ok "Test link invoked. Check if Unity Hub launches or focuses."
    else
      log_warn "xdg-open not found; cannot run test automatically."
    fi
  else
    log_info "You can test manually with: xdg-open 'unityhub://v1/editor-signin'"
  fi
}

main() {
  log_info "Ensuring required tools (optional)."
  ensure_deps_arch

  log_info "Detecting Unity Hub installation..."
  IFS='|' read -r install_type exec_cmd < <(detect_unityhub)
  log_info "Detected type: $install_type"
  if [[ -z "${exec_cmd:-}" ]]; then
    log_warn "Could not find Unity Hub executable automatically."
    log_warn "- If using Flatpak: install with 'flatpak install flathub com.unity.UnityHub'"
    log_warn "- If native (AUR): ensure 'unityhub' is in PATH"
    log_warn "- If AppImage: place it in ~/Applications and make it executable"
    log_error "Aborting—no Exec command available to create handler."
    exit 2
  fi
  log_info "Using Exec: $exec_cmd"

  local desktop_file
  desktop_file="$(create_handler_desktop "$exec_cmd")"

  register_mime_handler "$desktop_file"
  verify_registration "$desktop_file"

  cat <<'NOTE'
---
Next steps:
- Sign in from Unity Hub. When the browser finishes, ALLOW the prompt to open xdg-open/Unity Hub.
- If Thorium suppresses the external protocol prompt, try once with Firefox/Chromium to confirm.
---
NOTE

  maybe_test_open

  log_ok "Done. If login still fails, check the Hub's logs and share the outputs of:\n  which unityhub || true\n  flatpak info com.unity.UnityHub 2>/dev/null | sed -n '1,5p' || true\n  xdg-mime query default x-scheme-handler/unityhub\n  grep -R "x-scheme-handler/unityhub" ~/.local/share/applications /usr/share/applications 2>/dev/null | head -n 10"
}

main "$@"
